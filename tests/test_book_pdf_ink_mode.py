"""CARD-147 — the book interior is written black-and-white or in colour, and says which.

    AC-1   TestBookInk_BlackAndWhiteInteriorIsGrayscale
    AC-2   TestBookInk_ColourInteriorIsUnchanged
    AC-3   TestBookInk_ModeIsStoredAndDefaultsToBlackAndWhite
    AC-4   TestBookInk_PrintSetupAndFinaliseShowTheMode
    AC-5   TestBookInk_CoverIgnoresTheInteriorMode
    EC-1   TestBookInk_InkPositionsDoNotDependOnTheMode

    (CARD-337 adds TestBookInk_TheStreamReaderReadsOutsideStrings, which is
    not an AC: it is the control set for this module's own content-stream
    reader, in the shape CARD-306's review established.)

**There is no FR to cite, and that is deliberate.** This is owner intake —
``meta/architecture/inputs/raw-requirements.md``, 2026-09-25, "2 modes to pdf
generator: black/white and colors … I was a bit too creative making colored
pages for book 1 — then it gets more expensive. But we may add colors for
book2" — which the architect station has not formalised. CARD-144 cited FR-041,
the level-divider requirement, at about fifteen sites in order to look traced,
and its review charged it a finding for exactly that. The intake line is the
honest citation and it is the only one here.

What the card is, and what it is not
------------------------------------
The interior's **content** has always been pure black and white: COMP-007 draws
``INK = (0, 0, 0)`` on ``BACKGROUND = (255, 255, 255)`` and nothing else. So
this is not "remove the colours" — there are none. It is that the **file**
declared colour: every page was composed ``"RGB"``, JPEG-encoded in RGB and
written with ``/DeviceRGB``, which invites a print-on-demand interior's colour
price for a book with no colour in it. The book now stores which it is
(``books.interior_ink_mode``, migration 013) and the file says what the book
says.

**The measured surprise, recorded here because it is the opposite of what the
card predicted.** The card expected a grayscale interior to move every page's
recorded digest. It moves **none** of them. ``tests/helpers/pdf_pages.py``
reads a page back out of the PDF and normalises it to RGB, and a JPEG keeps the
luma plane: libjpeg's integer RGB->YCbCr maps a grey ``(v, v, v)`` to ``Y = v``
with ``Cb = Cr = 128``, the same luma quantisation table is used either way, and
``Cb = Cr = 128`` decodes back to ``R = G = B = Y`` exactly. So every page
decoded out of a grayscale interior is **byte-identical** to the matching page
decoded out of the RGB one (eleven of them, on the book this was first
recorded against before CARD-198 grew its answer section by one page), and
``book_baseline_card147.json`` records that as its finding rather than moved
digests. What *does* move is the file's length,
which is the whole point: one channel of JPEG instead of three.
:class:`TestBookInk_BlackAndWhiteInteriorIsGrayscale` asserts both halves — the
file declares ``DeviceGray`` and is materially smaller, and not one mark moved.

How the two modes are compared
------------------------------
Two independent readings, because each would hide something the other catches:

* **off the written file** — :func:`pdf_page_declarations` parses the PDF's own
  objects and reports each page's colour declaration **in the medium that page
  was written in**: the ``ColorSpace``, the ``ProcSet`` and the decoded page off
  an image XObject, and the colour-setting *operators* off a content stream.
  That is what a printer reads, and it is the only place "the file declares
  ``DeviceGray``" can be checked at all. It is a second implementation of what
  ``tests/helpers/pdf_pages.py`` does, deliberately: that helper normalises
  every page to RGB, which is precisely the fact under test here, so it cannot
  be the instrument.
* **off the page bitmaps before they are encoded** — the two images
  ``_write_page`` itself works with on one call: the ``"RGB"`` page COMP-007
  handed it and the page it handed the JPEG encoder. Both are captured off the
  writer rather than recomputed here, so the comparison is of the writer's own
  conversion (CLAUDE.md's "prefer an independent second implementation over
  re-deriving a value with the same function you're testing" — a test that
  called ``convert("L")`` itself would hold whatever the writer did). JPEG is
  lossy, so an exact "no mark moved" claim belongs on the bitmaps; the
  file-level reading then confirms that the loss is identical in the two
  colour spaces.

No ``hypothesis`` (it is not in the dependency baseline): EC-1's corpus is
built by hand with stdlib ``random.Random`` and asserts its own size, so it
cannot silently shrink (CLAUDE.md).

CARD-337 — what a page declares once it is not a bitmap
-------------------------------------------------------
Every reading above asks *what colour space the FILE declares*, and until
ADR-0042 every interior page was a JPEG that declared one. A page written as
operators has **no image XObject, no ``/ColorSpace`` and no
``BitsPerComponent``** — the reader raised ``KeyError: b'XObject'`` on it — so
the question had no subject in the converted medium. Two dispositions, per
claim, measured rather than argued, and the measurements are these: of the
baseline book's 14 interior pages **4 are still bitmaps and 10 are streams**,
because the registry declares ``DIVIDER`` raster; across EC-1's 14 books,
**40 of 171 pages** are bitmaps and every book has at least two.

**Re-expressed against the content stream** (ADR-0042/R6) where the claim has
an equivalent there, as a runtime property of the page and not a static fact
about the module:

* *written in one channel* → a vector page's only colour operators are ``g``
  and ``G``, it names no ``/ColorSpace`` resource, and none of PDF's other
  **ten** colour operators appears (:func:`assert_declares_one_grey`). The
  forbidden set is the whole vocabulary rather than the one operator that was
  expected — and it is an **ADR-0039/R3 named exemption**, not a derivation:
  see :data:`COLOUR_OPERATORS`, which names its authority, states its
  completeness and bounds its reach.
* *not one mark moved* → on a vector page the marks **are** the operators, so
  the two modes' streams are compared byte for byte. That is stricter than the
  bitmap equality it replaces, because it admits no encoder tolerance at all.
* *interior page 1 is the blank title page* → its stream carries **no painting
  operator at all**, which is a stronger statement than "every pixel is 255" —
  a page painting white on white satisfies the pixel reading and fails this
  one. The assertion is over the *operator set* (``not
  page["painting_operators"]``) and pins **no byte or token count**: a stream
  may carry graphics state, clipping or text positioning and still be blank by
  this reading, which is the right bound — those operators move no ink.
* *the corpus exercises three trims* → read off each page's ``MediaBox``
  (EC-019), not off a decoded image's size.
* *the writer's RGB→L conversion is the identity* → ``_write_page`` runs for a
  bitmap page only, so the **n-th write is no longer interior page n** (4
  writes for a 14-page interior). The write ordinal is translated through the
  written file's own list of bitmap pages.

**Retired, with a named survivor** — one claim, and this is the honest half:

* *the file declares the colour space the book chose* is **retired on vector
  pages**. There is no equivalent to re-express it against:
  ``book_vector.ContentStream``'s entire colour vocabulary is ``stroke_grey``
  and ``fill_grey``, there is no ``rg``, and a converted page therefore comes
  out ``DeviceGray`` **whichever mode the book stored**. Measured: the two
  modes' vector streams are identical. The **named survivor is the raster
  arm** — the same claim on the pages that are still bitmaps — and
  :func:`assert_mode_reached_the_file` asserts that arm is **non-empty** so the
  survivor cannot quietly die: if the interior ever holds no bitmap page, the
  stored mode reaches nothing in the file and that function refuses by name
  instead of looping over an empty list (ADR-0039/R1). ``EC1_MODE_PAGES`` is
  the corpus-wide form of the same floor.

**And the finding that goes with the retirement, which is not this card's to
fix (G-1).** The mode not reaching a converted page is a **product behaviour
change**, not a test defect: ``books.interior_ink_mode`` stops having any
effect on 10 of the baseline book's 14 interior pages, and the owner intake
this module cites — "we may add colors for book2" — is foreclosed on every
converted page, since the vector writer cannot emit a non-grey colour at all.
It is **CARD-322's**, routed the same way that card's ``cp1252`` refusal (M3b)
was.
"""

from __future__ import annotations

import random
import re
import uuid
import zlib
from io import BytesIO
from pathlib import Path
from typing import Any, Dict, List, Tuple

import numpy as np
import pytest
from PIL import Image, PdfParser

import nonogram.admin.book_manager as book_manager_module
from nonogram import clues
from nonogram.admin.book_manager import Book, BookManager, BookMetadata
from nonogram.admin.book_page_spec import (
    DEFAULT_INK_MODE,
    INK_MODE_COLUMN,
    InkMode,
    book_ink_mode,
    ink_mode_from_stored,
)
from nonogram.admin.book_pdf_generator import BookPDFGenerator
from nonogram.admin.book_plan import BUCKETS, TIERS, DistributionPlan, Split, bucket_of
from nonogram.admin.print_specs import PrintSpec, PrintSpecValidator
from tests.helpers.book_corpus import (
    BASELINE_PAGE_COUNT,
    baseline_puzzles,
    corpus_book,
    export_of,
    page_digests,
)
from tests.helpers.pdf_pages import pdf_page_count, pdf_pages

REPO_ROOT = Path(__file__).resolve().parents[1]

#: A pixel darker than this (0..255 grey) is ink — the level every other reader
#: of a book page in this suite uses.
INK_LEVEL = 128

#: How many books EC-1's corpus holds. Asserted inside the property test
#: against a literal, so neither the constant nor the loop can quietly shrink
#: it (the idiom at ``tests/test_books_list_plan_stats.py:808``; CARD-149's
#: review found a floor that could not fail).
EC1_BOOKS = 14

#: How many interior **pages** EC-1 compares across its whole corpus. A floor
#: on the pages and not only on the books: a corpus of fourteen one-page books
#: would satisfy a book count and prove nothing.
#:
#: 171 is the number the corpus above really produces — measured, not a bound
#: with room in it — so one page fewer fails. The literal in the assertion's
#: chain (``pages >= EC1_PAGES >= 110``) is what keeps this constant from being
#: quietly lowered to whatever a shrunken corpus happens to yield.
#:
#: **CARD-337 corrected this from 117, which was 54 pages of slack in a floor
#: whose own comment claimed it had none** (ADR-0039/R4: a figure recomputed
#: and refuted is retracted where it was written). Re-derived as 171 in both
#: media — the committed raster tree and the five-kind vector one give the
#: identical per-book counts ``[10, 13, 11, 14, 12, 18, 8, 10, 13, 11, 14, 11,
#: 18, 8]`` — so the staleness was never a conversion effect. The constant the
#: comment described and the constant the file held had drifted apart, and a
#: floor with 54 pages of room in it is the defect CARD-149's review found,
#: here in the very place that cites it.
#:
#: **167 since the answer key packs up to 20x25 four to a page** (owner,
#: 2026-11-09): four of the corpus's answer pages now share a page with
#: their neighbours, so the same fourteen books print four pages fewer.
EC1_PAGES = 167

#: How many of those pages the **stored ink mode actually reaches**: the pages
#: written as a bitmap, where a colour space is declared at all.
#:
#: A second floor, and CARD-337's reason for it: a vector page is
#: ``DeviceGray`` in either mode (``book_vector.ContentStream``'s whole colour
#: vocabulary is ``g``/``G``), so the mode-dependent half of EC-1 can only be
#: checked on bitmap pages. Without this floor the agreement half would still
#: pass over a corpus the mode had stopped touching — it would be comparing
#: each file with itself.
#:
#: 40 is the measured figure under the five-kind probe (2–4 DIVIDER pages per
#: book, present in all 14); the committed raster tree gives 171, every page.
#: The floor is the smaller, so it holds in both media, and it is tight in the
#: converted one — which is the point: if DIVIDER ever stops being a declared
#: bitmap (its ``expires_with`` names CARD-231), this fails by name instead of
#: passing over a claim with no subject left.
EC1_MODE_PAGES = 40


# --------------------------------------------------------------------------
# Reading a book PDF's own colour space
# --------------------------------------------------------------------------


def _pdf_name(value: Any) -> str:
    """One PDF name as plain text — ``PdfName(b'DeviceGray')`` -> ``"DeviceGray"``.

    Pillow's parser hands a ``/Name`` back as a :class:`PIL.PdfParser.PdfName`
    whose ``name`` is the bytes without the slash. Spelled out here so an
    assertion reads as the colour space a printer would see.
    """
    name = getattr(value, "name", value)
    return name.decode("ascii") if isinstance(name, bytes) else str(name)


#: Every operator PDF has for *setting a colour*, as the whole vocabulary and
#: not as the two this interior happens to use. ``g``/``G`` are
#: ``DeviceGray``; ``rg``/``RG`` ``DeviceRGB``; ``k``/``K`` ``DeviceCMYK``;
#: ``cs``/``CS`` select a named space and ``sc``/``scn``/``SC``/``SCN`` set a
#: component in it. :func:`stream_colour_operators` reports which of these a
#: vector page really contains, so "this page declares DeviceGray" is a claim
#: about all **twelve** and not a search for the one that was expected.
#:
#: **An ADR-0039/R3 named exemption, NOT a derivation** — and the distinction
#: is this card's own correction, because the prose called it "derived" and
#: that was false as written (AC-3, as corrected on main, asks for exactly
#: this form).
#:
#: * **Authority: PDF 32000-1 Table 74** ("Colour Operators"). It is an
#:   external file-format specification, so there is nothing the runtime can
#:   enumerate: this set is hand-written, and the honest label says so.
#:   Deriving it from the writer under test would be circular — it would make
#:   the very operator a plant emits part of the permitted vocabulary and
#:   therefore not forbidden.
#: * **Completeness:** these twelve are *all* of Table 74's colour operators.
#:   The cross-check in
#:   :meth:`TestTheStreamReader.test_the_forbidden_set_is_the_whole_colour_vocabulary`
#:   is a second hand-written literal, not a second reading of an authority —
#:   it catches a typo and an accidental edit to one of the two halves, and it
#:   is honestly not evidence of completeness against the spec. Completeness
#:   rests on the spec table, reviewed by eye.
#: * **Per-member failability:** each of the ten non-grey members is planted
#:   individually in that same cell and must make
#:   :func:`assert_declares_one_grey` raise — so no member is decoration
#:   (ADR-0039/R1).
#: * **The known bound, stated because the set's SHAPE is not deny-by-default.**
#:   :func:`stream_colour_operators` is an allow-list *filter*: it returns only
#:   tokens already in this set, and :func:`assert_declares_one_grey` then
#:   checks that result is a subset of ``GREY_COLOUR_OPERATORS``. So an
#:   operator *outside* this hand-written vocabulary is filtered out upstream
#:   and **passes silently** rather than failing as unclassifiable. The guard
#:   is therefore "none of the ten known non-grey ways to set a colour is
#:   used", not "nothing unrecognised sets a colour". That is sound for the
#:   claim it carries — Table 74 is closed, and a PDF cannot set a colour by
#:   any other operator — but it is a bound a reader must be told, not a
#:   deny-by-default guard mislabelled as one.
GREY_COLOUR_OPERATORS = frozenset({"g", "G"})
OTHER_COLOUR_OPERATORS = frozenset(
    {"rg", "RG", "k", "K", "cs", "CS", "sc", "scn", "SC", "SCN"}
)
COLOUR_OPERATORS = GREY_COLOUR_OPERATORS | OTHER_COLOUR_OPERATORS

#: Every operator that puts a mark on the page — path painting, text showing,
#: shading, inline and named images.
#:
#: **An ADR-0039/R3 named exemption on the same terms as
#: :data:`COLOUR_OPERATORS`**, and for the same reason: "this page paints
#: nothing" has to be a claim about the vocabulary, not about the operators a
#: blank page happens not to have used — but the vocabulary is hand-written
#: from a specification, not derived.
#:
#: * **Authority: PDF 32000-1 tables 59, 107 and 108** (path-painting, text-
#:   showing and XObject/inline-image operators), plus ``sh`` for shading.
#: * **Completeness:** all seventeen mark-making operators of those tables.
#: * **The same filter-shape bound:** :func:`stream_painting_operators`
#:   returns only tokens already in this set, so an unrecognised mark-making
#:   operator would be filtered out and read as "paints nothing". The blank
#:   title page is written by this project's own ``ContentStream``, whose
#:   emitted vocabulary is far narrower than these seventeen, so the bound has
#:   no live reach here — but it is the same bound and is recorded as one.
#: * **Failability is weaker here than for :data:`COLOUR_OPERATORS`, and this
#:   is the honest statement of it:** there is **no per-member plant** for
#:   these seventeen — none of this card's six plants targets the blank-page
#:   arm. What does hold every run is the *paired* arm: every interior page
#:   after page 1 asserts ``not blank``, so a set that failed to recognise a
#:   real mark-making operator would make a painted page read blank and red
#:   there. That is a live control on the set's **reach**, not on each
#:   member's necessity, and a member that no page ever emits is not shown
#:   failable by it.
PAINTING_OPERATORS = frozenset(
    {
        "S", "s", "f", "F", "f*", "B", "B*", "b", "b*",
        "Tj", "TJ", "'", '"',
        "sh", "Do", "BI", "EI",
    }
)

#: A token in a content stream, outside every ``(…)`` literal and ``<…>`` hex
#: body. Spelled as a scanner rather than a ``split()`` because ``"(0 0 1 rg)
#: Tj"`` is a *string* that says ``rg`` and is not a colour declaration — the
#: same distinction ``book_vector._paints_xobject`` makes for ``Do``, and the
#: reason that function exists rather than a substring search.
_STREAM_TOKEN = re.compile(rb"\(|<|[^\s()<>\[\]{}/%]+")


def stream_tokens(raw: bytes) -> List[str]:
    """``raw``'s operator tokens, with string and hex bodies skipped.

    An independent second implementation of the reading
    ``book_vector._paints_xobject`` does for one operator, written natively
    here rather than imported: CLAUDE.md's rule is that two capabilities
    needing the same logic reimplement it and cross-check, and the writer's
    own scanner is the thing under test.
    """
    tokens: List[str] = []
    index = 0
    end = len(raw)
    while index < end:
        match = _STREAM_TOKEN.search(raw, index)
        if match is None:
            break
        text = match.group()
        index = match.end()
        if text == b"(":
            # A PDF string literal: nested parentheses count, and a backslash
            # escapes the next byte.
            depth = 1
            while index < end and depth:
                byte = raw[index]
                if byte == 0x5C:  # backslash
                    index += 2
                    continue
                if byte == 0x28:  # (
                    depth += 1
                elif byte == 0x29:  # )
                    depth -= 1
                index += 1
            continue
        if text == b"<":
            closing = raw.find(b">", index)
            index = end if closing < 0 else closing + 1
            continue
        tokens.append(text.decode("latin-1"))
    return tokens


def stream_colour_operators(raw: bytes) -> set:
    """Which of :data:`COLOUR_OPERATORS` ``raw`` actually sets a colour with."""
    return {token for token in stream_tokens(raw) if token in COLOUR_OPERATORS}


def stream_painting_operators(raw: bytes) -> set:
    """Which of :data:`PAINTING_OPERATORS` ``raw`` actually marks the page with."""
    return {token for token in stream_tokens(raw) if token in PAINTING_OPERATORS}


def pdf_page_declarations(data: bytes) -> List[Dict[str, Any]]:
    """Every page of ``data``, with its colour declaration **in its own medium**.

    One dict per page, in page order, carrying ``medium`` — ``"raster"`` or
    ``"vector"`` — and then the fields that medium has:

    * a **raster** page is an image XObject, and declares its colour space the
      way a printer reads it: ``colour_space``, ``procset``, ``filter``,
      ``bits``, ``jpeg_bytes``, and ``image``, the page decoded **in the mode
      it was written in** (``"L"`` for grayscale, ``"RGB"`` for colour);
    * a **vector** page is a content stream, and declares its colour with
      *operators*: ``colour_operators`` (which of :data:`COLOUR_OPERATORS` it
      contains), ``painting_operators``, ``names_colorspace`` (whether the page
      names a ``/ColorSpace`` resource at all), ``procset``, and ``stream``,
      the decompressed operators.

    **Why this reader replaces the single-medium one, which is the whole of
    CARD-337.** The claim CARD-147 made is "the FILE declares what the book
    chose", and the only place that can be read is the file's own objects —
    which is why this exists beside ``tests/helpers/pdf_pages.py`` rather than
    calling it: that helper ends with ``.convert("RGB")``, normalising away the
    one thing this module is about. But once an interior page is written as
    operators (ADR-0042, CARD-322) it has **no image XObject and no
    ``/ColorSpace``**, and the old reader's ``resources[b"XObject"]`` raised
    ``KeyError`` on it — a claim meeting a page it cannot describe. Per
    ADR-0042/R6 the reading is re-expressed against the content stream, and as
    a **runtime** property of the page rather than a static fact about the
    module: each page is read in whichever medium the file says it is in, so
    one reader serves an all-raster interior, an all-vector one and the mixed
    one the registry actually produces.

    **A page this cannot classify is a failure, not a bucket** (ADR-0039/R2),
    and the declared reach is exactly this: a page with **one** image XObject
    is raster; a page with **no** XObject but a ``Contents`` object is vector;
    a page with **neither** is refused by name, and a page with **more than
    one** XObject is refused by the assertion above. A raster page *also* has
    a content stream — the ``Do`` that paints its image — so "has both" is the
    ordinary bitmap case and not an ambiguity; the XObject is read first
    because that is where a bitmap page keeps its colour space. A vector
    stream that is not ``FlateDecode`` raises out of :mod:`zlib` rather than
    being read as empty, which is the one remaining way this could be wrong
    and is loud.

    **None of those three refusal arms is demonstrated, and that is carded,
    not claimed.** This card's six plants exercise the classification's
    *reach* but none feeds this reader a page with neither an XObject nor a
    ``Contents``, a page with two XObjects, or a non-Flate stream — so the
    three refusals above are asserted and never shown to fire, which by this
    card's own AC-4 standard ("a retirement whose survivor cannot fail is a
    deletion") is a control this reader is owed. It is **CARD-365** (P2, 1c,
    depends on this card): three cases on hand-built PDF bytes in
    :class:`TestBookInk_TheStreamReaderReadsOutsideStrings`, deliberately
    *not* folded in here because adding cases after certification ships an
    uncertified final edit.
    """
    parser = PdfParser.PdfParser(buf=data)
    try:
        pages = []
        for number, ref in enumerate(parser.pages, start=1):
            page = parser.read_indirect(ref)
            resources = page[b"Resources"]
            procset = [_pdf_name(name) for name in resources.get(b"ProcSet", [])]
            xobjects = resources.get(b"XObject")
            if xobjects:
                assert len(xobjects) == 1, "a book page is exactly one image"
                (stream_ref,) = xobjects.values()
                stream = parser.read_indirect(stream_ref)
                image = Image.open(BytesIO(stream.buf))
                image.load()
                pages.append(
                    {
                        "medium": "raster",
                        "colour_space": _pdf_name(stream.dictionary[b"ColorSpace"]),
                        "procset": procset,
                        "filter": _pdf_name(stream.dictionary[b"Filter"]),
                        "bits": int(stream.dictionary[b"BitsPerComponent"]),
                        "jpeg_bytes": len(stream.buf),
                        "image": image,
                    }
                )
                continue
            contents = page.get(b"Contents")
            assert contents is not None, (
                f"page {number} has neither an image XObject nor a Contents "
                "object: it declares its colour in no medium this reader "
                "knows, and an unclassifiable page is a failure rather than a "
                "default (ADR-0039/R2)"
            )
            body = parser.read_indirect(contents)
            raw = zlib.decompress(body.buf)
            pages.append(
                {
                    "medium": "vector",
                    "procset": procset,
                    "names_colorspace": b"ColorSpace" in resources,
                    "colour_operators": stream_colour_operators(raw),
                    "painting_operators": stream_painting_operators(raw),
                    "stream": raw,
                }
            )
        return pages
    finally:
        parser.close()


def pdf_image_objects(data: bytes) -> List[Dict[str, Any]]:
    """``data``'s **raster** pages, as the file declares them.

    :func:`pdf_page_declarations`'s raster projection, and the reading every
    "what colour space does the file declare" claim below is gated on. On an
    all-raster file this is every page, which is what it has always been; on a
    converted interior it is the pages that are still bitmaps.

    It is deliberately **not** every page any more. A caller that wants "the
    declaration of page N whatever medium it is in" asks
    :func:`pdf_page_declarations`; a caller that wants "the colour space a
    printer reads off page N's image" asks this, and gets the pages that have
    one. The old reader conflated the two, and that conflation is the mechanism
    CARD-337 repaired: it made a page with no XObject an exception rather than
    a page with a different declaration.
    """
    return [page for page in pdf_page_declarations(data) if page["medium"] == "raster"]


def assert_declares_one_grey(pages: List[Dict[str, Any]], label: str) -> None:
    """Every vector page of ``pages`` declares ``DeviceGray`` and nothing else.

    The content-stream half of "the file is written in one channel": a page
    whose only colour operators are ``g``/``G`` sets its tone in
    ``DeviceGray``, names no other space and names no ``/ColorSpace`` resource
    to select one — the operator-level statement of what ``/DeviceGray`` says
    on a raster page.

    **This arm is MODE-INDEPENDENT and that is stated, not hidden.**
    ``book_vector.ContentStream``'s whole colour vocabulary is ``stroke_grey``
    and ``fill_grey``; there is no ``rg``/``RG`` in it, so a vector page comes
    out ``DeviceGray`` whichever mode the book stored. So this is a true claim
    about the file and **not** a re-expression of "the book's choice reached
    the page" — that claim is checked on the raster arm, which is where it
    still has a subject, and :func:`assert_mode_reached_the_file` asserts that
    arm is non-empty so it cannot pass vacuously.
    """
    for number, page in enumerate(pages, start=1):
        assert page["medium"] == "vector", f"{label} page {number}"
        assert page["colour_operators"] <= GREY_COLOUR_OPERATORS, (
            f"{label} vector page {number} sets a colour outside DeviceGray: "
            f"{sorted(page['colour_operators'] - GREY_COLOUR_OPERATORS)}"
        )
        assert not page["names_colorspace"], (
            f"{label} vector page {number} names a /ColorSpace resource, so it "
            "can select a space its operators do not name"
        )
        # The claim, and not the writer's current list: a page with no image
        # declares no image procset. Pinning `["PDF", "Text"]` outright would
        # be a guard that moves whenever an unrelated writer change touches
        # the resource dictionary — the mechanism that put a third of this
        # family's reds on the board.
        assert not {"ImageB", "ImageC", "ImageI"} & set(page["procset"]), (
            f"{label} vector page {number} declares an image procset "
            f"({page['procset']}) on a page that paints no image"
        )


def assert_mode_reached_the_file(
    raster: List[Dict[str, Any]], colour_space: str, procset: str, label: str
) -> None:
    """The raster arm: every bitmap page declares the space the book chose.

    **The named survivor of the claim CARD-337 retired on vector pages.** The
    first line is the whole point of the function: if the interior ever has no
    bitmap page left, the book's stored mode reaches nothing in the file at
    all, and this refuses LOUDLY instead of looping over an empty list and
    reading green (ADR-0039/R1 — a claim needs a control that can fail).
    """
    assert raster, (
        f"{label}: the interior has no raster page, so books.interior_ink_mode "
        "reaches nothing in the file and the claim that the file declares the "
        "mode the book chose has no subject anywhere. Retiring it needs a "
        "survivor, and this was it (CARD-337; DIVIDER is the last declared "
        "interior bitmap and its expires_with names CARD-231)"
    )
    for number, page in enumerate(raster, start=1):
        assert page["colour_space"] == colour_space, f"{label} raster page {number}"
        assert page["procset"] == ["PDF", procset], f"{label} raster page {number}"


def ink_mask(image: Image.Image) -> np.ndarray:
    """Which of ``image``'s pixels are ink, at full resolution and no tolerance.

    ``convert("L")`` on an already-grayscale page is the identity, and on a
    grey RGB page it is exact (ITU-R 601-2's three integer coefficients sum to
    65536), so the two modes are compared on the same quantity without either
    being favoured.
    """
    return np.asarray(image.convert("L")) < INK_LEVEL


def grey_levels(image: Image.Image) -> np.ndarray:
    """``image``'s luma as a 2-D array of 0..255."""
    return np.asarray(image.convert("L"))


class TestBookInk_TheStreamReaderReadsOutsideStrings:
    """Controls for CARD-337's own instrument, because it is a new reading.

    :func:`stream_colour_operators` is what "a vector page declares
    ``DeviceGray``" now rests on, and the reading has a trap: ``(0 0 1 rg) Tj``
    is a *string literal* that says ``rg`` and declares no colour at all. A
    substring search would call that page ``DeviceRGB`` and a page that really
    did set ``rg`` inside a text object would read the same, so the instrument
    would be both too wide and too narrow at once.

    That is not a hypothetical: CARD-306's review measured the first version of
    ``book_vector._paints_xobject`` — the same reading for the ``Do`` operator —
    being exactly both, which is why that function exists instead of a
    substring search and why its controls in
    ``tests/test_book_puzzle_page_vector.py`` run both string forms through it.
    This card reimplements that reading natively (CLAUDE.md: two capabilities
    needing the same logic reimplement and cross-check, rather than importing
    across), so it owes the same controls — a new instrument asserted only
    through the pages it happens to meet is a claim, not a reading.
    """

    @pytest.mark.parametrize(
        "raw,expected,why",
        [
            (b"0 g\n1 0 0 1 100 100 cm\n", {"g"}, "a plain grey fill"),
            (b"0.5 G\n", {"G"}, "a stroke grey"),
            (b"0 0 1 rg\n0 g\n", {"rg", "g"}, "both, outside strings"),
            (b"BT (0 0 1 rg) Tj ET", set(), "rg inside a string literal"),
            (b"BT (Scan Do now) Tj ET", set(), "a string that says Do"),
            (b"BT <30203020312072673E> Tj ET", set(), "rg inside a hex body"),
            (b"BT (nested (paren) 1 rg) Tj ET", set(), "nested parentheses"),
            (b"BT (escaped \\) 1 rg) Tj ET", set(), "an escaped close-paren"),
            (b"", set(), "an empty stream — the blank title page"),
        ],
    )
    def test_a_colour_operator_inside_a_string_is_not_a_declaration(
        self, raw, expected, why
    ):
        assert stream_colour_operators(raw) == expected, why

    @pytest.mark.parametrize(
        "raw,expected,why",
        [
            (b"", set(), "the blank title page paints nothing"),
            (b"100 100 m 200 200 l S", {"S"}, "a stroked path"),
            (b"BT (f) Tj ET", {"Tj"}, "an 'f' inside a string is not a fill"),
        ],
    )
    def test_a_painting_operator_inside_a_string_does_not_mark_the_page(
        self, raw, expected, why
    ):
        assert stream_painting_operators(raw) == expected, why

    def test_the_forbidden_set_is_the_whole_colour_vocabulary(self):
        """The forbidden set is the vocabulary, not the operator expected.

        ``GREY_COLOUR_OPERATORS`` and ``OTHER_COLOUR_OPERATORS`` partition
        ``COLOUR_OPERATORS``, and the whole of PDF's colour vocabulary is in
        it — so a page setting ``DeviceCMYK`` or selecting a named space is
        caught by :func:`assert_declares_one_grey`, not only one setting
        ``rg``.

        **What this cell is and is not** (ADR-0039/R3, not R2). The literal
        below is a **second hand-written spelling** of the same twelve
        operators, not a second reading of an authority: it catches a typo and
        an accidental edit to either half, and it is *not* evidence that the
        set is complete against PDF 32000-1 Table 74 — completeness is the
        named exemption's claim, resting on the spec table. What this cell
        does prove is the half that matters most: the loop below plants each
        of the ten non-grey members in turn and requires
        :func:`assert_declares_one_grey` to raise, so **no member is
        decoration**. See :data:`COLOUR_OPERATORS` for the exemption's
        authority, completeness and the filter-shape bound.
        """
        assert GREY_COLOUR_OPERATORS | OTHER_COLOUR_OPERATORS == COLOUR_OPERATORS
        assert not GREY_COLOUR_OPERATORS & OTHER_COLOUR_OPERATORS
        assert COLOUR_OPERATORS == {
            "g", "G", "rg", "RG", "k", "K", "cs", "CS", "sc", "scn", "SC", "SCN"
        }
        for operator in OTHER_COLOUR_OPERATORS:
            page = {
                "medium": "vector",
                "names_colorspace": False,
                "procset": ["PDF", "Text"],
                "colour_operators": {"g", operator},
                "painting_operators": {"f"},
                "stream": b"",
            }
            with pytest.raises(AssertionError, match="sets a colour outside"):
                assert_declares_one_grey([page], "a planted page")


# --------------------------------------------------------------------------
# Books
# --------------------------------------------------------------------------


def book_on(mode: InkMode | None, book_id: str = "card-147") -> Book:
    """The baseline book, on CON-018's Book 1 profile, printed ``mode``.

    ``None`` stores nothing in the column, which is every book that existed
    before migration 013 — the case AC-3 is about.
    """
    book = corpus_book(book_id)
    book.interior_ink_mode = mode.value if mode is not None else None
    return book


def interiors_both_ways(puzzles, book_id: str = "card-147") -> Tuple[bytes, bytes]:
    """The same book's interior exported black-and-white, then colour.

    One function, so the two exports cannot differ in anything but the mode:
    the same puzzle list, the same stored trim and margins, the same call.
    """
    bw = export_of(BookPDFGenerator(book_on(InkMode.BLACK_AND_WHITE, book_id)), puzzles)
    colour = export_of(BookPDFGenerator(book_on(InkMode.COLOUR, book_id)), puzzles)
    return bw, colour


@pytest.fixture(scope="module")
def baseline_exports() -> Tuple[bytes, bytes]:
    """The baseline book (:data:`BASELINE_PAGE_COUNT` pages), exported both ways."""
    return interiors_both_ways(baseline_puzzles())



# --------------------------------------------------------------------------
# AC-1
# --------------------------------------------------------------------------


class TestBookInk_BlackAndWhiteInteriorIsGrayscale:
    """A black-and-white book's interior is grayscale, and no mark moved (AC-1).

    Three claims, each measured rather than reasoned about:

    * every page of the file is written in one 8-bit channel and the PDF
      declares ``/DeviceGray`` with the grayscale procset ``/ImageB`` — which
      is what makes the file honest about a book that has no colour in it;
    * the ink is **pixel-for-pixel the same marks** as the RGB rendering, on
      the page bitmaps (exact, before the lossy encode) and on the pages
      decoded back out of the two files (also exact, as it turns out);
    * and the conversion softens nothing (G-2, ADR-0037/R2): pure black stays
      0, pure white stays 255, and the conversion invents no level between
      them.
    """

    def test_every_page_declares_devicegray_and_one_channel(self, baseline_exports):
        """Every page is written in one channel — each in its own medium.

        The page **count** is medium-independent and stays the whole claim it
        was. The declaration is read where that page keeps it: off the image
        XObject for a bitmap page, off the operators for a vector one
        (ADR-0042/R6).
        """
        bw, _colour = baseline_exports
        pages = pdf_page_declarations(bw)

        assert len(pages) == BASELINE_PAGE_COUNT, "the corpus cannot silently shrink"

        raster = [page for page in pages if page["medium"] == "raster"]
        assert_mode_reached_the_file(raster, "DeviceGray", "ImageB", "the grey interior")
        for number, page in enumerate(raster, start=1):
            assert page["filter"] == "DCTDecode", f"raster page {number}"
            assert page["bits"] == 8, f"raster page {number}"
            assert page["image"].mode == "L", f"raster page {number}"

        assert_declares_one_grey(
            [page for page in pages if page["medium"] == "vector"],
            "the grey interior",
        )

    def test_the_colour_export_of_the_same_book_declares_devicergb(
        self, baseline_exports
    ):
        """The control: the difference really is the mode and not the export.

        **And the control's reach is now asserted rather than assumed.** It
        runs on the pages the mode still reaches — the bitmap ones — and
        :func:`assert_mode_reached_the_file` fails if there are none. The
        vector pages of the *colour* export declare ``DeviceGray`` too, which
        is measured below rather than glossed: ``ContentStream`` has no
        ``rg``, so the colour mode cannot reach a converted page at all. That
        is this card's finding against CARD-322, and asserting it here is what
        keeps it from being re-discovered as a mystery.
        """
        _bw, colour = baseline_exports
        pages = pdf_page_declarations(colour)
        raster = [page for page in pages if page["medium"] == "raster"]
        assert_mode_reached_the_file(raster, "DeviceRGB", "ImageC", "the colour interior")
        for number, page in enumerate(raster, start=1):
            assert page["image"].mode == "RGB", f"raster page {number}"

        assert_declares_one_grey(
            [page for page in pages if page["medium"] == "vector"],
            "the colour interior",
        )

    def test_no_mark_moves_on_any_page_bitmap(self, monkeypatch):
        """The exact half: the page **the writer encoded** is the same ink (G-2).

        Compared before the JPEG encode, where "pixel-for-pixel" can be
        asserted without a tolerance at all.

        The grayscale page is not computed here. It is the very
        :class:`~PIL.Image.Image` ``_write_page`` handed to the JPEG encoder,
        captured off that one call, and the RGB page it is compared against is
        the one ``_write_page`` was handed on the same call — so both sides of
        the equality come out of the writer and the assertion binds to the
        writer's own conversion. Calling ``page.convert("L")`` in this test
        instead would re-derive the value under test with the same function
        the writer uses, and would therefore hold whatever the writer did
        (CLAUDE.md: "prefer an independent second implementation over
        re-deriving a value with the same function you're testing"; the
        measured consequence was that a softening injected into ``_write_page``
        left this test green while the two file-level readings below killed
        it).

        What is checked is that the writer's conversion is the identity on
        luma: the encoded grayscale page equals the RGB page's own single
        channel, every ink position is the same position, and the set of
        levels is unchanged, so no anti-aliasing was introduced and no rule
        was softened.

        Each page is compared **inside its own write** and both images are
        dropped when that frame returns, so nothing is collected and
        CARD-145's streaming property is not traded away to take the
        measurement (G-3).

        **CARD-337: the write ordinal is not the interior page ordinal.**
        ``_write_page`` runs for a *bitmap* page only — ``_write_pdf`` sends a
        vector page to ``write_vector_page`` instead — so once any interior
        kind is written as operators, "the n-th write" and "interior page n"
        stop being the same number (measured: 4 writes for a 14-page
        interior). This test used both identities: ``number = checked + 1`` as
        a page number, and ``checked == BASELINE_PAGE_COUNT`` as a page count.
        Both are now **derived from the written file** — the interior page
        numbers that really are bitmaps, read out of the page tree — so the
        reading is a runtime property of the export rather than a static
        assumption about the medium (ADR-0042/R6). The page *total* keeps its
        literal, because that total is medium-independent.
        """
        generator = BookPDFGenerator(book_on(InkMode.BLACK_AND_WHITE))
        assert generator.interior_bitmap_mode == "L"

        # Which interior pages this book writes as bitmaps, read off the file
        # itself. The export is taken unpatched, so the mapping is the
        # writer's own and not a prediction from the registry.
        declarations = pdf_page_declarations(
            export_of(BookPDFGenerator(book_on(InkMode.BLACK_AND_WHITE)),
                      baseline_puzzles())
        )
        assert len(declarations) == BASELINE_PAGE_COUNT == 14, (
            f"the interior is {len(declarations)} pages, not {BASELINE_PAGE_COUNT}"
        )
        raster_page_numbers = [
            number
            for number, page in enumerate(declarations, start=1)
            if page["medium"] == "raster"
        ]
        assert raster_page_numbers, (
            "no interior page is a bitmap, so _write_page is never called and "
            "there is no writer conversion to compare: this test's whole "
            "subject would be gone and it would pass having measured nothing "
            "(CARD-337, ADR-0039/R1)"
        )

        real_write_page = BookPDFGenerator._write_page
        real_save = Image.Image.save
        encoded: List[Image.Image] = []
        checked = 0

        def recording_save(image, *args, **kwargs):
            """Every image handed to an encoder, in the order it was handed."""
            encoded.append(image)
            return real_save(image, *args, **kwargs)

        def write_page_and_compare(self, pdf, page, *args, **kwargs):
            """``_write_page``, then compare what it encoded with what it got."""
            nonlocal checked
            before = len(encoded)
            result = real_write_page(self, pdf, page, *args, **kwargs)
            written = encoded[before:]
            del encoded[before:]

            assert len(written) == 1, "a book page is encoded exactly once"
            # CARD-337: the write's own ordinal, translated into the interior
            # page it is writing.
            assert checked < len(raster_page_numbers), (
                f"_write_page ran {checked + 1} times for an interior with "
                f"{len(raster_page_numbers)} bitmap page(s)"
            )
            number = raster_page_numbers[checked]
            grey_page = written[0]

            assert page.mode == "RGB", "COMP-007 draws the page in RGB either way"
            assert grey_page.mode == "L", (
                f"page {number}: the writer encoded {grey_page.mode!r}"
            )
            rgb = np.asarray(page)
            grey = np.asarray(grey_page)

            # The three channels of a book page are equal to begin with: the
            # interior has no colour to lose. Asserted, not assumed — if a
            # future page ever drew one, the claims below would be false.
            assert np.array_equal(rgb[:, :, 0], rgb[:, :, 1])
            assert np.array_equal(rgb[:, :, 1], rgb[:, :, 2])

            # ... so the conversion is the identity on the page's own levels.
            assert np.array_equal(grey, rgb[:, :, 0]), f"page {number} moved"
            assert np.array_equal(grey < INK_LEVEL, rgb[:, :, 0] < INK_LEVEL)

            # G-2: pure black stays 0, pure white stays 255, and no level that
            # was not already on the page appears.
            assert set(np.unique(grey).tolist()) <= set(
                np.unique(rgb[:, :, 0]).tolist()
            ), f"page {number} gained a grey level the RGB page did not have"
            assert int((grey == 0).sum()) == int((rgb[:, :, 0] == 0).sum())
            assert int((grey == 255).sum()) == int((rgb[:, :, 0] == 255).sum())
            # CARD-206: interior page 1 is the blank title / copyright page
            # and carries no ink at all, so it has no pure black to compare.
            # The non-vacuity claim is made on every *other* page and the
            # title page's blankness is asserted outright, rather than the
            # claim being loosened to "some page carries black".
            #
            # CARD-337: `number` is now the interior page this write is
            # writing, so this branch fires when page 1 really is the bitmap
            # being written and does not fire when page 1 is a content stream
            # — where the blankness claim is read off the stream instead, in
            # `test_the_two_files_hold_the_same_marks_page_for_page` and in
            # EC-1's agreement test. The branch is not loosened: it is read in
            # the medium the page is in.
            if number == 1:
                assert int((grey == 255).sum()) == grey.size, (
                    "interior page 1 is the blank title page (CARD-206)"
                )
            else:
                assert int((grey == 0).sum()) > 0, (
                    f"page {number} carries no pure black"
                )
            checked += 1
            return result

        monkeypatch.setattr(Image.Image, "save", recording_save)
        monkeypatch.setattr(BookPDFGenerator, "_write_page", write_page_and_compare)
        export_of(generator, baseline_puzzles())

        # CARD-206: BASELINE_PAGE_COUNT is 14 (CARD-200's thirteen, plus the
        # blank title / copyright page reserved as interior page 1) and the
        # literal beside it is pinned above, on the page *total*, which is
        # medium-independent. What is pinned here is that every bitmap page the
        # file holds was compared — derived from the file, because a literal
        # here would be a count of writes and that is a medium fact (CARD-337).
        assert checked == len(raster_page_numbers), (
            f"{checked} of {len(raster_page_numbers)} bitmap page(s) compared"
        )

    def test_the_two_files_hold_the_same_marks_page_for_page(self, baseline_exports):
        """And the same after the encode: the two files decode to one ink.

        The claim the card's "nothing moves, nothing is lost" makes about the
        *file*, which is what a printer sees. It holds exactly — JPEG keeps the
        luma plane and constant chroma planes decode back to it — so this is an
        equality and not an overlap ratio.
        """
        bw, colour = baseline_exports
        grey_pages = pdf_page_declarations(bw)
        colour_pages = pdf_page_declarations(colour)

        assert pdf_page_count(bw) == pdf_page_count(colour) == BASELINE_PAGE_COUNT
        compared = {"raster": 0, "vector": 0}
        for number, (g, c) in enumerate(zip(grey_pages, colour_pages, strict=True), 1):
            assert g["medium"] == c["medium"], (
                f"interior page {number} is {g['medium']} in the grey export and "
                f"{c['medium']} in the colour one: the mode decided a medium"
            )
            if g["medium"] == "raster":
                assert g["image"].size == c["image"].size, f"interior page {number}"
                assert np.array_equal(
                    ink_mask(g["image"]), ink_mask(c["image"])
                ), f"interior page {number}: the ink moved"
                assert np.array_equal(
                    grey_levels(g["image"]), grey_levels(c["image"])
                ), f"interior page {number}: a level moved"
                blank = int(ink_mask(g["image"]).sum()) == 0
            else:
                # CARD-337, ADR-0042/R6: on a vector page the marks ARE the
                # operators, so "not one mark moved" is the content streams
                # being identical — a stricter equality than the bitmap one,
                # not a looser one, because it admits no encoder tolerance at
                # all. Measured identical across the two modes, which is this
                # card's finding stated as an assertion:
                # `book_vector.ContentStream` has no `rg` to emit.
                assert g["stream"] == c["stream"], (
                    f"interior page {number}: {len(g['stream'])} vs "
                    f"{len(c['stream'])} stream bytes — a mark moved with the mode"
                )
                blank = not g["painting_operators"]
            compared[g["medium"]] += 1

            # CARD-206's blank title / copyright page, read in the medium it
            # was written in: no ink on a bitmap, no painting operator at all
            # on a content stream. This is the survivor the writer-side test's
            # own page-1 branch names when page 1 is not a bitmap.
            # Since 2026-11-09 page 1 is the title / copyright page (the owner
            # replaced the blank one): it carries type, so it has marks too.
            if number == 1:
                assert not blank, "interior page 1 is the title page and carries its type"
            else:
                assert not blank, f"interior page {number} carries no marks"

        assert sum(compared.values()) == BASELINE_PAGE_COUNT, compared

    @pytest.mark.parametrize(
        "mode,colour_space",
        [(InkMode.BLACK_AND_WHITE, "DeviceGray"), (InkMode.COLOUR, "DeviceRGB")],
    )
    def test_the_file_the_owner_downloads_is_the_one_the_book_chose(
        self, panel, mode, colour_space
    ):
        """End to end, through the route Finalise's button posts to.

        Everything above exports through the generator. This closes the loop
        the owner actually walks: choose the mode on Print setup's form,
        press Download interior PDF on Finalise, and read the colour space off
        the bytes that come back as an attachment. Nothing between the two
        screens is stubbed.
        """
        book_id = panel.book()
        panel.submit_print_setup(book_id, interior_ink_mode=mode.value)

        downloaded = panel.download_interior(book_id)
        pages = pdf_page_declarations(downloaded)
        raster = [page for page in pages if page["medium"] == "raster"]
        # CARD-337: the bitmap pages are where the stored mode still reaches
        # the file, and `assert_mode_reached_the_file` refuses if there are
        # none — so "the file the owner downloads is the one the book chose"
        # cannot come out green on a file the choice never touched.
        assert_mode_reached_the_file(
            raster, colour_space, "ImageB" if colour_space == "DeviceGray" else "ImageC",
            f"the downloaded {mode.value} interior",
        )
        assert {page["colour_space"] for page in raster} == {colour_space}
        assert_declares_one_grey(
            [page for page in pages if page["medium"] == "vector"],
            f"the downloaded {mode.value} interior",
        )
        assert f'data-interior-ink-mode="{mode.value}"' in panel.finalise(book_id), (
            "and Finalise names the mode the file was written in"
        )

    def test_the_grayscale_file_is_materially_smaller(self, baseline_exports):
        """Size is one of the card's three stated reasons, so it is measured.

        One channel of JPEG where there were three. The bound is loose on
        purpose — what is asserted is that the saving is real and
        page-for-page, not a particular ratio, which depends on how much ink a
        page carries.
        """
        bw, colour = baseline_exports
        assert len(bw) < len(colour)

        # CARD-337: the saving is a property of the JPEG pages — one channel
        # where there were three — so it is read on the pages that have a
        # JPEG. A vector page's stream is identical in the two modes (measured
        # above), so it contributes nothing to the saving and has no
        # per-page claim to make here. `assert_mode_reached_the_file` on the
        # grey side is what keeps this from being an empty loop.
        grey_pages = pdf_image_objects(bw)
        colour_pages = pdf_image_objects(colour)
        assert grey_pages, (
            "the interior has no JPEG page, so one channel instead of three "
            "saves nothing and this claim has no subject (CARD-337)"
        )
        for number, (g, c) in enumerate(zip(grey_pages, colour_pages, strict=True), 1):
            assert g["jpeg_bytes"] < c["jpeg_bytes"], f"raster page {number}"

        saved = 1 - len(bw) / len(colour)
        assert 0.05 < saved < 0.5, f"the grayscale interior saved {saved:.1%}"


# --------------------------------------------------------------------------
# AC-2
# --------------------------------------------------------------------------


class TestBookInk_ColourInteriorIsUnchanged:
    """A colour book agrees with black-and-white pixel for pixel (AC-2).

    **CARD-201 note (SCOPE+, retired rather than silently adjusted).** Until
    this card, this class checked AC-2 by comparing the colour interior's
    pages 1-8 against ``book_baseline_card146.json`` — a recording made
    **before** CARD-147 existed, at the page *positions* that recording used.
    That premise — "pages 2-8 sit at the same interior position every card
    since has left alone" — was already fragile (CARD-198's own note above
    this one flagged it once) and CARD-201 breaks it outright: the guide
    grows from one page to two, so every page from the first puzzle/divider
    page onward moves one page later **and its parity flips** (inserting a
    page always flips recto/verso for everything after it), and COMP-007
    mirrors a book page's margins by parity (ADR-0036). A page's *content* is
    unchanged (G-2), but its pixels are not, so a positional byte comparison
    against a pre-CARD-201 recording would fail on every one of those pages
    for a reason that has nothing to do with colour — exactly the false
    positive this class's own CARD-198 note already warned was one card away.

    Rather than re-splice a third historical fixture at yet another offset,
    this class is retired down to what it was already telling its own reader
    was the real coverage: AC-2 — colour and black-and-white agree pixel for
    pixel on *every* page — is fully covered, without any positional fixture
    at all, by
    :meth:`TestBookInk_BlackAndWhiteInteriorIsGrayscale.test_the_two_files_hold_the_same_marks_page_for_page`
    above, which compares the two *live* exports to each other, page for
    page, on whatever the current book's page count and positions are. The
    one test kept here is the sanity check that a positional comparison could
    never have substituted for anyway: that both files really did move
    together and stay ordered.
    """

    def test_black_and_white_is_shorter_than_colour_at_the_current_length(
        self, baseline_exports
    ):
        """Both files are the current book's length, and B&W stays smaller."""
        bw, colour = baseline_exports
        assert pdf_page_count(bw) == pdf_page_count(colour) == BASELINE_PAGE_COUNT
        assert len(bw) < len(colour)


# --------------------------------------------------------------------------
# AC-3
# --------------------------------------------------------------------------


class TestBookInk_ModeIsStoredAndDefaultsToBlackAndWhite:
    """The mode is stored, survives a reopen, and defaults to black-and-white (AC-3).

    "Every existing book" is three different books, and each is checked:

    * a book whose column holds ``NULL`` — a row from before migration 013;
    * a book whose column holds the empty string — what a form that submitted
      a blank field would leave;
    * and a ``books`` row that migration 013 has actually upgraded, which is
      where the backfill is executed rather than described.
    """

    @pytest.mark.parametrize("stored", [None, "", "   "])
    def test_a_book_with_nothing_stored_is_black_and_white(self, stored):
        assert ink_mode_from_stored(stored) is InkMode.BLACK_AND_WHITE
        assert ink_mode_from_stored(stored) is DEFAULT_INK_MODE
        assert book_ink_mode(book_on(None)) is InkMode.BLACK_AND_WHITE

    def test_a_book_that_is_not_a_book_at_all_is_black_and_white(self):
        """``BookPDFGenerator(None)`` is CON-018's profile, and its ink too."""
        assert book_ink_mode(None) is InkMode.BLACK_AND_WHITE
        assert BookPDFGenerator().interior_bitmap_mode == "L"

    @pytest.mark.parametrize(
        "mode,bitmap", [(InkMode.BLACK_AND_WHITE, "L"), (InkMode.COLOUR, "RGB")]
    )
    def test_each_mode_names_one_bitmap_mode(self, mode, bitmap):
        assert mode.bitmap_mode == bitmap
        assert BookPDFGenerator(book_on(mode)).interior_bitmap_mode == bitmap

    def test_a_value_nobody_can_print_is_refused_naming_the_column(self):
        """Not silently read as one of the two (the ``_stored_mm`` posture)."""
        with pytest.raises(ValueError) as raised:
            ink_mode_from_stored("greyscale")
        assert INK_MODE_COLUMN in str(raised.value)
        assert "'bw'" in str(raised.value) and "'colour'" in str(raised.value)

        # And through the book, which is how every reader asks.
        with pytest.raises(ValueError) as raised:
            book_ink_mode(_odd_book())
        assert INK_MODE_COLUMN in str(raised.value)

        # A generator cannot be built for such a book at all, so no file is
        # written in a colour space nobody chose.
        with pytest.raises(ValueError):
            BookPDFGenerator(_odd_book())

    def test_the_mode_is_stored_and_survives_a_reopen(self, panel):
        """Written through the real setter, read back through a fresh get_book."""
        book_id = panel.book()
        assert book_ink_mode(panel.books.get_book(book_id)) is InkMode.BLACK_AND_WHITE

        panel.books.set_print_spec(
            book_id, PrintSpec("21.59", "27.94", interior_ink_mode="colour")
        )
        reopened = panel.books.get_book(book_id)
        assert reopened.interior_ink_mode == "colour"
        assert book_ink_mode(reopened) is InkMode.COLOUR

        panel.books.set_print_spec(
            book_id, PrintSpec("21.59", "27.94", interior_ink_mode="bw")
        )
        assert book_ink_mode(panel.books.get_book(book_id)) is InkMode.BLACK_AND_WHITE

    def test_a_spec_that_names_no_mode_leaves_the_stored_one_alone(self, panel):
        """"The caller said nothing" is not "set it to the default"."""
        book_id = panel.book()
        panel.books.set_print_spec(
            book_id, PrintSpec("21.59", "27.94", interior_ink_mode="colour")
        )
        panel.books.set_print_spec(book_id, PrintSpec("20.32", "25.40"))
        reopened = panel.books.get_book(book_id)
        assert reopened.trim_width_cm == "20.32", "the trim was stored"
        assert book_ink_mode(reopened) is InkMode.COLOUR, "and the mode was kept"

    def test_the_storage_boundary_refuses_a_mode_the_reader_would_refuse(self, panel):
        book_id = panel.book()
        with pytest.raises(ValueError) as raised:
            panel.books.set_print_spec(
                book_id, PrintSpec("21.59", "27.94", interior_ink_mode="sepia")
            )
        assert "interior ink mode" in str(raised.value)
        assert book_ink_mode(panel.books.get_book(book_id)) is InkMode.BLACK_AND_WHITE

    def test_the_validator_accepts_the_two_modes_and_nothing_else(self):
        for mode in InkMode:
            assert PrintSpecValidator.validate_interior_ink_mode(mode.value) == (
                True,
                None,
            )
        assert PrintSpecValidator.validate_interior_ink_mode(None)[0] is True
        assert PrintSpecValidator.validate_interior_ink_mode("")[0] is True
        valid, error = PrintSpecValidator.validate_interior_ink_mode("mono")
        assert valid is False and "mono" in error

    def test_create_spec_fills_the_default(self):
        spec, error = PrintSpecValidator.create_spec("21.59", "27.94")
        assert error is None
        assert spec.interior_ink_mode == DEFAULT_INK_MODE.value == "bw"
        assert spec.to_dict()["interior_ink_mode"] == "bw"


def _odd_book() -> Book:
    """A book whose stored mode is one nobody can print."""
    book = corpus_book("card-147-odd")
    book.interior_ink_mode = "greyscale"
    return book


class TestBookInk_Migration013BackfillsEveryExistingBook:
    """AC-3's stored half: migration 013 gives every existing row ``'bw'``.

    Executed, not described. The database is built in today's shape, the
    column is dropped back off to make it a pre-013 row, a book is inserted
    into it by the pre-013 code path, and then 013 is actually run.

    SQLite here rather than Postgres because the suite must run without a
    server (the project's DB-mode tests skip when there is none). The
    migration uses ``batch_alter_table`` and a portable ``UPDATE`` built from
    SQLAlchemy's expression language, so what is exercised is the statement
    both backends run; the Postgres path was additionally run by hand against
    ``nonogram_test`` and is reported on the card.
    """

    @pytest.fixture
    def pre_013_db(self, tmp_path, monkeypatch):
        from sqlalchemy import create_engine, text

        from nonogram.db.models import Base

        path = tmp_path / "pre013.db"
        url = f"sqlite:///{path}"
        engine = create_engine(url)
        Base.metadata.create_all(engine)
        with engine.begin() as connection:
            connection.execute(
                text("ALTER TABLE books DROP COLUMN interior_ink_mode")
            )
            connection.execute(
                text(
                    "INSERT INTO books (id, title, puzzle_ids, puzzle_titles, "
                    "book_metadata, status) VALUES "
                    "('11111111-1111-1111-1111-111111111111', 'Book 1', "
                    "'[]', '{}', '{}', 'draft')"
                )
            )
        engine.dispose()

        monkeypatch.setenv("DATABASE_URL", url)
        from alembic import command

        command.stamp(self._config(url), "012")
        return url

    @staticmethod
    def _config(url: str):
        from alembic.config import Config

        config = Config()
        config.set_main_option("script_location", str(REPO_ROOT / "migrations"))
        config.set_main_option("sqlalchemy.url", url)
        return config

    @staticmethod
    def _books(url: str):
        from sqlalchemy import create_engine, inspect, text

        engine = create_engine(url)
        try:
            columns = {c["name"] for c in inspect(engine).get_columns("books")}
            with engine.connect() as connection:
                if "interior_ink_mode" in columns:
                    rows = connection.execute(
                        text("SELECT title, interior_ink_mode FROM books")
                    ).all()
                else:
                    rows = connection.execute(text("SELECT title FROM books")).all()
            return columns, rows
        finally:
            engine.dispose()

    def test_the_fixture_really_is_a_pre_013_database(self, pre_013_db):
        columns, rows = self._books(pre_013_db)
        assert "interior_ink_mode" not in columns
        assert len(rows) == 1, "the book the upgrade has to reach"

    def test_upgrade_adds_the_column_and_backfills_the_existing_book(
        self, pre_013_db
    ):
        from alembic import command

        command.upgrade(self._config(pre_013_db), "013")

        columns, rows = self._books(pre_013_db)
        assert "interior_ink_mode" in columns
        assert [(title, mode) for title, mode in rows] == [("Book 1", "bw")]
        assert ink_mode_from_stored(rows[0][1]) is InkMode.BLACK_AND_WHITE

    def test_a_book_inserted_after_the_upgrade_is_black_and_white_too(
        self, pre_013_db
    ):
        """The column's own default, so a row written without naming it is 'bw'."""
        from alembic import command
        from sqlalchemy import create_engine, text

        command.upgrade(self._config(pre_013_db), "013")
        engine = create_engine(pre_013_db)
        try:
            with engine.begin() as connection:
                connection.execute(
                    text(
                        "INSERT INTO books (id, title, puzzle_ids, puzzle_titles, "
                        "book_metadata, status) VALUES "
                        "('22222222-2222-2222-2222-222222222222', 'Book 2', "
                        "'[]', '{}', '{}', 'draft')"
                    )
                )
                stored = connection.execute(
                    text(
                        "SELECT interior_ink_mode FROM books WHERE title = 'Book 2'"
                    )
                ).scalar()
        finally:
            engine.dispose()
        assert stored == "bw"

    def test_the_downgrade_takes_the_column_back_off(self, pre_013_db):
        from alembic import command

        command.upgrade(self._config(pre_013_db), "013")
        command.downgrade(self._config(pre_013_db), "012")
        columns, rows = self._books(pre_013_db)
        assert "interior_ink_mode" not in columns
        assert len(rows) == 1, "and takes no book with it"


# --------------------------------------------------------------------------
# AC-4
# --------------------------------------------------------------------------


class TestBookInk_PrintSetupAndFinaliseShowTheMode:
    """Print setup offers the choice and Finalise names it (AC-4).

    The owner has to be able to see which of the two the file they are about to
    upload will be, because that is what it is priced on. Both screens are read
    as the owner sees them — the rendered HTML — and the choice is made through
    the real form POST, not by writing the column.
    """

    def test_print_setup_offers_both_modes_with_the_stored_one_checked(self, panel):
        book_id = panel.book()
        shown = panel.print_setup(book_id)

        for mode in InkMode:
            assert f'value="{mode.value}"' in shown, mode
            assert mode.label in shown, mode
        assert 'name="interior_ink_mode"' in shown
        # The stored mode is the one that comes back checked.
        assert _checked_ink_mode(shown) == "bw"

    def test_choosing_colour_on_the_form_stores_it_and_comes_back_checked(
        self, panel
    ):
        book_id = panel.book()
        panel.submit_print_setup(book_id, interior_ink_mode="colour")

        assert book_ink_mode(panel.books.get_book(book_id)) is InkMode.COLOUR
        assert _checked_ink_mode(panel.print_setup(book_id)) == "colour"

    def test_a_submission_that_names_no_mode_keeps_the_stored_one(self, panel):
        """A client built before this card cannot flip a colour book."""
        book_id = panel.book()
        panel.submit_print_setup(book_id, interior_ink_mode="colour")
        panel.submit_print_setup(book_id, interior_ink_mode=None)
        assert book_ink_mode(panel.books.get_book(book_id)) is InkMode.COLOUR

    def test_an_unknown_mode_is_refused_and_stores_nothing(self, panel):
        book_id = panel.book()
        response = panel.submit_print_setup(book_id, interior_ink_mode="sepia")
        shown = response.get_data(as_text=True)
        assert response.status_code == 200, "refused in place, not redirected"
        assert "Interior ink mode must be" in shown
        assert book_ink_mode(panel.books.get_book(book_id)) is InkMode.BLACK_AND_WHITE
        assert panel.books.get_book(book_id).trim_width_cm == "21.59", (
            "a refused mode stores no trim either"
        )

    @pytest.mark.parametrize(
        "mode,label", [(InkMode.BLACK_AND_WHITE, "Black and white"), (InkMode.COLOUR, "Colour")]
    )
    def test_finalise_names_the_mode(self, panel, mode, label):
        book_id = panel.book()
        panel.submit_print_setup(book_id, interior_ink_mode=mode.value)
        shown = panel.finalise(book_id)
        assert f'data-interior-ink-mode="{mode.value}"' in shown
        assert "Interior ink" in shown
        assert label in shown

    def test_finalise_says_so_when_the_stored_mode_cannot_be_read(self, panel):
        """The posture the Trim size row already takes for an unreadable trim."""
        book_id = panel.book()
        panel.books.get_book(book_id).interior_ink_mode = "sepia"
        shown = panel.finalise(book_id)
        assert "Cannot be read — set it again on Print setup" in shown
        assert "data-interior-ink-mode" not in shown


def _checked_ink_mode(html: str) -> str:
    """Which interior-ink radio the rendered form came back with checked.

    Read off the markup rather than off the context, so what is asserted is
    what the owner's browser is given.
    """
    checked = [
        mode.value
        for mode in InkMode
        if f'id="ink_{mode.value}" value="{mode.value}"\n' in html
        and "checked" in html.split(f'id="ink_{mode.value}"', 1)[1].split(">", 1)[0]
    ]
    assert len(checked) == 1, f"expected one checked radio, found {checked}"
    return checked[0]


# --------------------------------------------------------------------------
# AC-5
# --------------------------------------------------------------------------


class TestBookInk_CoverIgnoresTheInteriorMode:
    """An uploaded colour cover stays colour on a black-and-white book (AC-5).

    The cover is a separate file (FR-043, CARD-135) holding an image the owner
    supplied, which may be anything; a colour cover on a black-and-white
    interior is the ordinary KDP case, not a mistake to correct. G-4 keeps the
    cover path out of this card's scope, so what is asserted is that the mode
    does not reach it.
    """

    @staticmethod
    def _colour_cover(width: int, height: int) -> Image.Image:
        """An unmistakably coloured cover: three bands no grey can imitate."""
        cover = Image.new("RGB", (width, height), (10, 20, 200))
        pixels = np.asarray(cover).copy()
        pixels[: height // 3] = (220, 30, 40)
        pixels[height // 3 : 2 * height // 3] = (30, 200, 60)
        return Image.fromarray(pixels, "RGB")

    def test_the_cover_file_of_a_black_and_white_book_is_devicergb(self):
        generator = BookPDFGenerator(book_on(InkMode.BLACK_AND_WHITE))
        assert generator.interior_bitmap_mode == "L", "the interior really is grey"

        cover = generator.export_cover(
            "Winter Pictures",
            self._colour_cover(generator.page_width_px, generator.page_height_px),
        ).getvalue()

        (page,) = pdf_image_objects(cover)
        assert page["colour_space"] == "DeviceRGB"
        assert page["procset"] == ["PDF", "ImageC"]
        assert page["image"].mode == "RGB"

    def test_the_cover_still_carries_colour(self):
        """Not merely declared RGB: the pixels are not grey."""
        generator = BookPDFGenerator(book_on(InkMode.BLACK_AND_WHITE))
        cover = generator.export_cover(
            "Winter Pictures",
            self._colour_cover(generator.page_width_px, generator.page_height_px),
        ).getvalue()

        pixels = np.asarray(pdf_image_objects(cover)[0]["image"], dtype=np.int16)
        spread = (
            pixels.max(axis=2) - pixels.min(axis=2)
        )  # 0 everywhere on a grey page
        assert spread.max() > 100, "the cover came out grey"
        assert float((spread > 20).mean()) > 0.5, "most of the cover lost its colour"

    def test_the_generated_title_cover_is_devicergb_too(self):
        """No uploaded image, and still the cover's own colour space."""
        generator = BookPDFGenerator(book_on(InkMode.BLACK_AND_WHITE))
        cover = generator.export_cover("Winter Pictures").getvalue()
        (page,) = pdf_image_objects(cover)
        assert page["colour_space"] == "DeviceRGB"
        assert page["image"].mode == "RGB"

    def test_export_book_writes_a_grey_interior_beside_a_colour_cover(self):
        """Both files of one export, each in its own colour space."""
        generator = BookPDFGenerator(book_on(InkMode.BLACK_AND_WHITE))
        export = generator.export_book(
            baseline_puzzles(),
            "Winter Pictures",
            self._colour_cover(generator.page_width_px, generator.page_height_px),
        )
        interior = export.interior.getvalue()
        cover = export.cover.getvalue()

        assert export.interior_page_count == BASELINE_PAGE_COUNT
        # CARD-337: the interior's claim is read per medium; the cover's is
        # not, because a cover is a photograph and ADR-0042/R2 declares it
        # raster with an empty `expires_with` — no card converts it, which is
        # why the three sibling tests above stay a single-medium reading.
        interior_pages = pdf_page_declarations(interior)
        assert_mode_reached_the_file(
            [page for page in interior_pages if page["medium"] == "raster"],
            "DeviceGray", "ImageB", "the grey interior beside a colour cover",
        )
        assert_declares_one_grey(
            [page for page in interior_pages if page["medium"] == "vector"],
            "the grey interior beside a colour cover",
        )
        assert [page["colour_space"] for page in pdf_image_objects(cover)] == [
            "DeviceRGB"
        ]


# --------------------------------------------------------------------------
# EC-1
# --------------------------------------------------------------------------


def ec1_books(seed: int = 147) -> List[Dict[str, Any]]:
    """EC-1's corpus: books that differ in every way the mode must not touch.

    Trim, both side margins, the puzzle sizes, the clue depths, the tier runs
    and therefore the page count, the pairing verdicts and the answer-key
    packing all vary; the mode is the one thing held apart and applied twice to
    each book. Sizes and depths come from a seeded ``random.Random`` drawn in a
    fixed order, so the corpus is the same on every run and on every machine
    (no ``hypothesis`` — it is not in the dependency baseline).

    The trims are real KDP ones and two of them are not the Book 1 profile, so
    "the gutter, the origin and the cell do not depend on the mode" is asserted
    on sheets whose gutter, origin and cell genuinely differ from each other.
    """
    rng = random.Random(seed)
    trims = [
        # CON-018's Book 1 profile, whose outside margin became 0.5 in on
        # 2026-10-17 (CARD-222); the three "0.95" below are kept as what they
        # now are — an ordinary stored margin of 9.5 mm — because the point of
        # this corpus is sheets that differ from each other, not the profile.
        ("21.59", "27.94", "1.27", "1.27"),  # CON-018's Book 1 profile
        ("15.24", "22.86", "1.27", "0.95"),  # 6 x 9 in
        ("20.32", "25.40", "1.59", "0.95"),  # 8 x 10 in, a wider gutter
        ("21.00", "29.70", "1.27", "0.64"),  # A4, the narrowest legal outside
    ]
    tier_runs = [
        ("easy", "easy"),
        ("easy", "easy", "medium"),
        ("medium", "hard"),
        ("easy", "medium", "hard"),
        ("hard", "hard", "hard"),
        ("easy", "easy", "medium", "medium", "hard"),
        ("medium",),
    ]

    books: List[Dict[str, Any]] = []
    for index in range(EC1_BOOKS):
        trim = trims[index % len(trims)]
        tiers = tier_runs[index % len(tier_runs)]
        puzzles = []
        for position, tier in enumerate(tiers, start=1):
            side = rng.choice((10, 12, 15, 18, 20, 25, 30))
            depth = rng.choice((3, 4, 5))
            if 2 * depth - 1 > side:
                depth = 3
            puzzles.append(
                _ec1_puzzle(f"card147-{index}-{position}", side, depth, tier, position)
            )
        books.append({"label": f"book {index} on {trim[0]}x{trim[1]} cm",
                      "trim": trim, "puzzles": puzzles})
    return books


def _ec1_puzzle(
    puzzle_id: str, side: int, depth: int, tier: str, number: int
) -> Dict[str, Any]:
    limit = 2 * depth - 1
    grid = [
        [x % 2 == 0 and x < limit and y % 2 == 0 and y < limit for x in range(side)]
        for y in range(side)
    ]
    found = clues.compute_clues(grid)
    return {
        "id": puzzle_id,
        "grid": grid,
        "clues_rows": [list(clue) for clue in found.rows],
        "clues_cols": [list(clue) for clue in found.columns],
        "width": side,
        "height": side,
        "puzzle_name": f"Picture {number}",
        "difficulty_tier": tier,
    }


def _ec1_book(trim, mode: InkMode) -> Book:
    width, height, gutter, outside = trim
    return Book(
        book_id="card-147-ec1",
        metadata=BookMetadata(
            title="EC-1",
            description="",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=width,
        trim_height_cm=height,
        gutter_margin_cm=gutter,
        outside_margin_cm=outside,
        interior_ink_mode=mode.value,
    )


class TestBookInk_InkPositionsDoNotDependOnTheMode:
    """EC-1, as a property over a corpus: the mode changes the colour space only.

    *For any book and any mode, the set of inked pixel positions is identical;
    cell size, origin, gutter, rules, frame and page count do not depend on
    it.* Stated as a standing property, so it is verified over
    :data:`EC1_BOOKS` books that differ in trim, both side margins, puzzle
    sizes, clue depths, tier runs, pairing verdicts and page count — never on
    one book.

    Every claim is read off the written files and nothing is asked of the
    generator: the page count comes out of the PDF's page tree, the printed
    size out of each page's ``MediaBox`` (the only thing that says how large
    the raster is *printed*), and the ink out of the decoded pages. The two
    colour spaces are asserted to differ in the same loop, so a run in which
    both exports came out the same way cannot pass as agreement.

    The floor is an exact chain — ``checked >= EC1_BOOKS >= 12`` — and a
    second one on the pages compared, because fourteen one-page books would
    satisfy a book count and prove nothing. CARD-149's review found a floor
    that could not fail; this one can.
    """

    @pytest.fixture(scope="class")
    @classmethod
    def exports(cls):
        """Every corpus book's interior, both ways. Built once for the class."""
        built = []
        for entry in ec1_books():
            bw = export_of(
                BookPDFGenerator(_ec1_book(entry["trim"], InkMode.BLACK_AND_WHITE)),
                entry["puzzles"],
            )
            colour = export_of(
                BookPDFGenerator(_ec1_book(entry["trim"], InkMode.COLOUR)),
                entry["puzzles"],
            )
            built.append((entry["label"], bw, colour))
        return built

    def test_the_corpus_is_the_size_it_claims_and_varies(self, exports):
        """The corpus's own floors: enough books, enough lengths, enough trims.

        **CARD-337, ADR-0042/R6.** The trim variety used to be read as the
        decoded size of page 1's image, which a content-stream page does not
        have. The medium-durable statement of a trim is the page's
        ``MediaBox`` — EC-019's own claim, and the quantity this class's
        docstring already calls "the only thing that says how large the raster
        is *printed*". So it is re-expressed against the page object, which is
        strictly better evidence of a trim than a pixel count at an assumed
        DPI, and holds in either medium.
        """
        from tests.helpers.page_ink import pdf_page_boxes

        assert len(exports) == EC1_BOOKS >= 12, f"the corpus shrank to {len(exports)}"
        page_counts = {pdf_page_count(bw) for _label, bw, _c in exports}
        assert len(page_counts) >= 4, (
            f"the corpus's books all have the same length ({page_counts}); a "
            "property over one page count is an example"
        )
        trims = {pdf_page_boxes(bw)[0] for _label, bw, _c in exports}
        assert len(trims) >= 3, f"the corpus exercises only {len(trims)} trims"

    def test_the_two_modes_agree_on_every_page_of_every_book(self, exports):
        from tests.helpers.page_ink import pdf_page_boxes

        books = 0
        pages = 0
        mode_reached = 0
        for label, bw, colour in exports:
            grey_pages = pdf_page_declarations(bw)
            colour_pages = pdf_page_declarations(colour)

            # The page count is the file's own, read out of its page tree.
            assert pdf_page_count(bw) == pdf_page_count(colour) == len(grey_pages), label
            assert len(grey_pages) == len(colour_pages), label

            # The printed size of every page, in PDF points.
            assert pdf_page_boxes(bw) == pdf_page_boxes(colour), label

            # CARD-337: the mode-dependent half of the property has to run on
            # this book, or its agreement half is comparing a file with
            # itself. Asserted per book, not once for the corpus.
            grey_raster = [p for p in grey_pages if p["medium"] == "raster"]
            assert_mode_reached_the_file(
                grey_raster, "DeviceGray", "ImageB", f"{label} (grey)"
            )
            assert_mode_reached_the_file(
                [p for p in colour_pages if p["medium"] == "raster"],
                "DeviceRGB", "ImageC", f"{label} (colour)",
            )
            mode_reached += len(grey_raster)

            for number, (g, c) in enumerate(
                zip(grey_pages, colour_pages, strict=True), start=1
            ):
                assert g["medium"] == c["medium"], (
                    f"{label} page {number}: {g['medium']} vs {c['medium']} — "
                    "the mode decided a medium"
                )
                if g["medium"] == "raster":
                    # The modes really did differ on this page ...
                    assert g["colour_space"] == "DeviceGray", f"{label} page {number}"
                    assert c["colour_space"] == "DeviceRGB", f"{label} page {number}"
                    assert g["image"].mode == "L" and c["image"].mode == "RGB"

                    # ... and the ink is in exactly the same places.
                    assert g["image"].size == c["image"].size, f"{label} page {number}"
                    grey_ink, colour_ink = ink_mask(g["image"]), ink_mask(c["image"])
                    assert np.array_equal(grey_ink, colour_ink), (
                        f"{label} page {number}: "
                        f"{int(np.logical_xor(grey_ink, colour_ink).sum())} "
                        "pixels of ink moved with the mode"
                    )
                    assert np.array_equal(
                        grey_levels(g["image"]), grey_levels(c["image"])
                    ), f"{label} page {number}: a grey level moved with the mode"
                    blank = int(grey_ink.sum()) == 0
                else:
                    # CARD-337, ADR-0042/R6: a vector page's marks are its
                    # operators, so the agreement is the streams being
                    # identical. The mode-dependence claim is NOT re-expressed
                    # here and is not asserted here: it is retired on vector
                    # pages, with the raster arm above as its named survivor,
                    # because `ContentStream`'s colour vocabulary is `g`/`G`
                    # only and a vector page is DeviceGray in either mode.
                    assert g["stream"] == c["stream"], (
                        f"{label} page {number}: a mark moved with the mode"
                    )
                    # The label carries the real page number, because the
                    # helper numbers the list it is handed and a one-page list
                    # would otherwise call page 12 "page 1".
                    assert_declares_one_grey([g], f"{label} (grey) page {number} of")
                    assert_declares_one_grey([c], f"{label} (colour) page {number} of")
                    blank = not g["painting_operators"]

                # CARD-206: interior page 1 is the blank title / copyright
                # page — no marks on either mode's copy of it, which is itself
                # the thing to assert here; every other page must carry marks,
                # or the equality above would be comparing two empty pages.
                # Since 2026-11-09 page 1 is the title / copyright page, so
                # it carries marks like every other page.
                if number == 1:
                    assert not blank, (
                        f"{label} page 1 is the title page and carries its type"
                    )
                else:
                    assert not blank, f"{label} page {number} has no marks"
                pages += 1
            books += 1

        assert books == EC1_BOOKS >= 12, f"only {books} books compared"
        assert pages >= EC1_PAGES >= 110, f"only {pages} pages compared"
        assert mode_reached >= EC1_MODE_PAGES >= 14, (
            f"the stored mode reached only {mode_reached} page(s) of the corpus"
        )

    def test_the_mode_never_reaches_the_sheet(self):
        """The other half of EC-1: ``PageSpec`` does not carry the mode at all.

        The geometry is built by ``book_page_spec`` from the stored trim and
        margins, so two books differing only in their ink mode produce the
        *same object*. Asserted on the spec rather than on a page, because that
        is where a mode leaking into the geometry would first show (ADR-0036/R1).
        """
        for entry in ec1_books():
            grey = BookPDFGenerator(_ec1_book(entry["trim"], InkMode.BLACK_AND_WHITE))
            colour = BookPDFGenerator(_ec1_book(entry["trim"], InkMode.COLOUR))
            for page_number in (1, 2, 7):
                assert grey.page_spec(page_number) == colour.page_spec(page_number)
            assert (grey.page_width_px, grey.page_height_px) == (
                colour.page_width_px,
                colour.page_height_px,
            )
            assert grey.interior_bitmap_mode != colour.interior_bitmap_mode

    def test_the_page_plan_is_the_same_plan(self):
        """Page count, pairing and the packed key are decided without the mode.

        ``interior_stream`` settles all three before a pixel exists, so the
        cheapest place to see a mode leaking into them is there — and it costs
        no drawing, which is what makes the whole corpus affordable here.
        """
        checked = 0
        for entry in ec1_books():
            grey = BookPDFGenerator(
                _ec1_book(entry["trim"], InkMode.BLACK_AND_WHITE)
            ).interior_stream(entry["puzzles"])
            colour = BookPDFGenerator(
                _ec1_book(entry["trim"], InkMode.COLOUR)
            ).interior_stream(entry["puzzles"])
            assert grey.page_count == colour.page_count, entry["label"]
            assert grey.unpaired_page_count == colour.unpaired_page_count, entry["label"]
            assert grey.answer_page_count == colour.answer_page_count, entry["label"]
            checked += 1
        assert checked == EC1_BOOKS >= 12, f"only {checked} books compared"


# --------------------------------------------------------------------------
# The panel
# --------------------------------------------------------------------------


@pytest.fixture
def panel(monkeypatch):
    """The admin panel in memory mode, with a book store of its own."""
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.setenv("TESTING", "true")
    monkeypatch.setattr(
        book_manager_module, "_book_manager", BookManager(session_factory=None)
    )
    from nonogram.admin.app import create_app

    app = create_app()
    app.config["TESTING"] = True
    return Panel(app)


class Panel:
    """A panel, one book on it, and the two screens AC-4 is about."""

    def __init__(self, app):
        self.app = app
        self.client = app.test_client()
        self.books = app.book_manager
        self.store = app.puzzle_review_service

    def book(self, title: str = "Winter") -> str:
        """A draft book holding two puzzles, on a plan the gate accepts."""
        book_id = self.books.create_book(title, "a book", "generic", "adults")
        records = [
            dict(_ec1_puzzle(str(uuid.uuid4()), 15, 4, "easy", 1), status="approved", book_id=None),
            dict(_ec1_puzzle(str(uuid.uuid4()), 15, 4, "medium", 2), status="approved", book_id=None),
        ]
        for record in records:
            self.store.puzzles[record["id"]] = record
        self.books.add_puzzles_to_book(book_id, [r["id"] for r in records])
        self.books.save_plan(book_id, _plan_of(records))
        return book_id

    def print_setup(self, book_id: str) -> str:
        response = self.client.get(f"/book/{book_id}/setup-print")
        assert response.status_code == 200, response.status_code
        return response.get_data(as_text=True)

    def submit_print_setup(self, book_id: str, *, interior_ink_mode, **extra):
        data = {"unit": "cm", "width": "21.59", "height": "27.94", **extra}
        if interior_ink_mode is not None:
            data["interior_ink_mode"] = interior_ink_mode
        return self.client.post(f"/book/{book_id}/setup-print", data=data)

    def finalise(self, book_id: str) -> str:
        response = self.client.get(f"/book/{book_id}/finalize")
        assert response.status_code == 200, response.status_code
        return response.get_data(as_text=True)

    def download_interior(self, book_id: str) -> bytes:
        """The interior PDF Finalise's own button posts for (FR-043)."""
        response = self.client.post(
            f"/book/{book_id}/finalize",
            data={"action": "download_pdf", "part": "interior"},
        )
        assert response.status_code == 200, response.status_code
        assert response.mimetype == "application/pdf"
        return response.get_data()


def _plan_of(records) -> DistributionPlan:
    """A plan whose matrix is this selection, so the readiness gate is silent."""
    count = len(records)
    cells = [[0] * len(TIERS) for _ in BUCKETS]
    for record in records:
        bucket = bucket_of(record["width"], record["height"])
        tier = next(t for t in TIERS if t.value == record["difficulty_tier"])
        cells[BUCKETS.index(bucket)][TIERS.index(tier)] += 1
    matrix = tuple(tuple(row) for row in cells)
    columns = tuple(sum(row[t] for row in cells) for t in range(len(TIERS)))
    rounded = [round(100 * column / count) for column in columns]
    rounded[0] += 100 - sum(rounded)
    for easy, medium, hard in [tuple(rounded)] + [
        (e, m, 100 - e - m) for e in range(101) for m in range(101 - e)
    ]:
        candidate = DistributionPlan(
            count=count, split=Split(easy, medium, hard), cells=matrix
        )
        if not candidate.disagrees_with_split:
            return candidate
    raise AssertionError("no split agrees with this selection")


# The owner's 2026-11-09 polish took the frame off and lets every answer pack;
# this module measures what it measured before (tests/helpers/legacy_book_layout.py).
from tests.helpers.legacy_book_layout import module_fixture as _legacy_module_fixture  # noqa: E402

_legacy_book_layout = _legacy_module_fixture()
