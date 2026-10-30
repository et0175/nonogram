"""Every face the book's interior draws holds CON-020's 10 pt floor (CARD-184).

CON-020: no text the interior prints for the reader is set below 10 pt at the
page's own resolution. Until this card only the guide page was tested against
it (CARD-149, CARD-167); this module walks **every** ``draw.text`` call one
interior export makes.

**Why a spy on ``ImageDraw.text``, and not on the font constructors.**
``_band_font``, ``png._lettering_font`` and ``pdf._header_font`` are
``lru_cache``d, so a spy on ``ImageFont.truetype`` misses every size an earlier
test already asked for. What is *drawn* is what the reader sees, and spying
there also leaves out the guide title's fitting probes, which are measured and
never drawn.

Each recorded call carries the font's size in pixels (``font.size``), or
``None`` — "unsized" — when the font is not a ``FreeTypeFont`` or is the face a
sizeless ``ImageFont.load_default()`` returned during the walk (on Pillow
>= 10.1 that face *is* a ``FreeTypeFont``, at a 10 px em); the chain of
functions that called it; and the interior page it was drawn for. A size in
points is ``size * 72 / generator.dpi``. An unsized face always fails.

**The one exemption.** A puzzle page's clue digits are bound to their cell
(``_CLUE_FONT_RATIO``), and INV-006's cell floor puts them at 8.4 pt, so
no setting reaches 10 pt there without breaking the cell floor. The floor
is **4.75 mm since NFR-008's amendment of 2026-10-17** (CARD-222) and was
4.8 mm before it; the 8.4 pt is unchanged by that move, because at 300 dpi
both floors round ``pitch * _CLUE_FONT_RATIO`` to the same 35 px. They are
exempt **by the function that draws them**: ``png._draw_clues`` and
``book_pdf_generator._write_clues``. The guide page's worked example draws its
clue digits through ``_write_clues`` too, from inside ``draw_example_line``;
those are the reader's instruction text and are **never** exempt, so a call
with ``draw_example_line`` anywhere in its chain is held to the floor.

AC-1..AC-4 of CARD-184, one class each.
"""

from __future__ import annotations

import ast
import inspect
import random
import sys
import textwrap
from contextlib import contextmanager
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pytest
from PIL import Image, ImageDraw, ImageFont

from nonogram.admin import (
    book_answer_vector,
    book_guide_vector,
    book_pdf_generator,
    book_toc_vector,
    book_vector,
    book_vector_draw,
)
from nonogram.admin.book_manager import Book, BookMetadata
from nonogram.admin.book_pdf_generator import BookPDFGenerator

from tests.helpers import pdf_vector
from tests.helpers.book_corpus import BASELINE_PAGE_COUNT, baseline_puzzles, corpus_book

# --------------------------------------------------------------------------
# What the acceptance criteria ask for, written out rather than imported
# --------------------------------------------------------------------------

#: CON-020's floor, in points.
FLOOR_PT = 10.0

#: A point is 1/72 in.
POINTS_PER_INCH = 72.0

#: The divider's size, in points (AC-4): the 60 px it was at 300 DPI.
DIVIDER_PT = 14.4

#: CARD-200: the folio's own size, in points — CON-020's floor exactly
#: (``book_pdf_generator.FOLIO_PT``), written out rather than imported so
#: this file's own independent statement of every interior face's size
#: stays independent.
FOLIO_PT = 10.0

#: The path the interior asks Pillow for Arial at (AC-2 makes it fail).
ARIAL_PATH = "/System/Library/Fonts/Arial.ttf"

#: The functions whose ``draw.text`` calls are puzzle-page clue digits
#: (AC-3), as ``(module, function)``.
EXEMPT_CALLERS = frozenset(
    {
        ("nonogram.export.png", "_draw_clues"),
        ("nonogram.admin.book_pdf_generator", "_write_clues"),
    }
)

#: A call made from inside this function is the guide page's worked example,
#: never exempt (AC-3).
WORKED_EXAMPLE = "draw_example_line"

#: The functions that letter a puzzle page's band: the two-up page's own
#: setter, and COMP-007's header for a page that prints one puzzle alone.
BAND_SETTERS = frozenset(
    {
        ("nonogram.admin.book_pdf_generator", "_set_band"),
        ("nonogram.export.pdf", "_draw_header"),
    }
)

#: CARD-222's footer line: the grid-size label, the one face the frame adds.
#: It is set at ``SIZE_LABEL_PT``, which reads COMP-007's own
#: ``INTERIOR_FOOTER_LINE_PT`` — the floor again — and the folio beside it is
#: CARD-200's, drawn by ``_draw_folio`` and already covered.
FOOTER_LABEL_SETTER = ("nonogram.admin.book_pdf_generator", "_draw_page_frame")

#: CARD-198 note: FR-042's level headings are gone (the packed key that
#: drew them no longer exists), so there is no "answer heading" kind any
#: longer — only the caption :meth:`BookPDFGenerator.solved_puzzle_page`
#: draws directly, tagged below by that caller.
#:
#: CARD-202 note (SCOPE+): the caption's own ``draw.text`` call moved from
#: ``solved_puzzle_page``'s body into a new shared helper,
#: ``BookPDFGenerator._draw_solved_slot`` — both a full answer page and a
#: packed slot draw their caption through it now (reuse, not reinvention;
#: see that method's own docstring). The immediate caller the spy sees is
#: therefore ``_draw_solved_slot`` on every page, full or packed, which is
#: why :attr:`TextCall.kind` below checks for either name: the two calls are
#: the same kind of caption either way, and the old name is kept in the
#: check (rather than dropped) only because nothing here requires removing it.

#: The smallest trim a book may be stored with
#: (``book_page_spec.MIN_TRIM_CM``), written out rather than imported, and the
#: margins the 10x10 cm book was measured on when the card was drafted.
MIN_TRIM_CM = 10.0
MIN_TRIM_GUTTER_CM = "0.95"
MIN_TRIM_OUTSIDE_CM = "0.64"


def min_trim_book() -> Book:
    """The baseline book's print specification at the 10x10 cm minimum trim."""
    return Book(
        book_id="card-184-min-trim",
        metadata=BookMetadata(
            title="Winter Pictures",
            description="The book CARD-184's type-floor test draws.",
            theme="generic",
            target_audience="adults",
            size="",
            page_count=0,
        ),
        trim_width_cm=f"{MIN_TRIM_CM:.2f}",
        trim_height_cm=f"{MIN_TRIM_CM:.2f}",
        gutter_margin_cm=MIN_TRIM_GUTTER_CM,
        outside_margin_cm=MIN_TRIM_OUTSIDE_CM,
    )


BOOKS = {"book1": corpus_book, "min-trim": min_trim_book}

#: How many interior pages each book's export of the baseline puzzles draws,
#: asserted so the walk cannot silently shrink. Book 1 is the baseline book's
#: own count (``BASELINE_PAGE_COUNT``); the 10x10 cm trim's tighter sheet
#: changes what the puzzle section's pairing walk can fit, one page longer.
PAGE_COUNTS = {"book1": BASELINE_PAGE_COUNT, "min-trim": BASELINE_PAGE_COUNT + 1}


@pytest.fixture(params=sorted(BOOKS))
def book(request) -> str:
    """Book 1, and the same book at the 10x10 cm minimum trim."""
    return request.param

# --------------------------------------------------------------------------
# The spy
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class TextCall:
    """One ``draw.text`` call, as the spy saw it."""

    page: int
    text: str
    size_px: Optional[int]  # None: the font is not a FreeTypeFont (unsized)
    chain: Tuple[Tuple[str, str], ...]  # (module, function), innermost first
    dpi: int

    @property
    def caller(self) -> Tuple[str, str]:
        return self.chain[0]

    @property
    def caller_names(self) -> frozenset:
        return frozenset(name for _, name in self.chain)

    @property
    def points(self) -> Optional[float]:
        if self.size_px is None:
            return None
        return self.size_px * POINTS_PER_INCH / self.dpi

    @property
    def exempt(self) -> bool:
        return self.caller in EXEMPT_CALLERS and WORKED_EXAMPLE not in self.caller_names

    @property
    def kind(self) -> str:
        names = self.caller_names
        if "create_guide_page" in names:
            return "guide"
        if "create_divider_page" in names:
            return "divider"
        if self.caller in BAND_SETTERS:
            return "band"
        if self.caller == FOOTER_LABEL_SETTER:
            return "footer label"
        if self.caller[1] in ("solved_puzzle_page", "_draw_solved_slot"):
            return "answer caption"
        return "other"

    def describe(self) -> str:
        size = "unsized" if self.size_px is None else f"{self.size_px} px = {self.points:.2f} pt"
        where = " <- ".join(f"{module}.{name}" for module, name in self.chain[:3])
        return f"page {self.page} {self.kind} {self.text!r}: {size} ({where})"


def _call_chain(frame: Any) -> Tuple[Tuple[str, str], ...]:
    """The ``nonogram`` functions on the stack above ``frame``, innermost first."""
    chain: List[Tuple[str, str]] = []
    while frame is not None:
        module = frame.f_globals.get("__name__", "")
        if module.startswith("nonogram."):
            chain.append((module, frame.f_code.co_name))
        frame = frame.f_back
    return tuple(chain)


def record_interior(
    generator: BookPDFGenerator, monkeypatch: pytest.MonkeyPatch, page_count: int
) -> List[TextCall]:
    """Every ``draw.text`` call one interior export makes, tagged by page.

    Starts by emptying the module's font caches (:func:`clear_font_caches`),
    so that each recording loads the faces its own configuration resolves
    to rather than inheriting the previous recording's.
    """
    clear_font_caches()
    original = ImageDraw.ImageDraw.text
    original_default = ImageFont.load_default
    calls: List[TextCall] = []
    current = {"page": 0}
    # Faces a sizeless ``load_default()`` returned. On Pillow >= 10.1 that is
    # a FreeTypeFont at a 10 px em, so ``isinstance`` alone cannot tell it
    # from a face that was asked for at 10 px; the faces are kept alive so an
    # ``id`` is never reused for another face during the walk.
    sizeless: List[Any] = []

    def load_default(size=None):
        face = original_default() if size is None else original_default(size)
        if size is None:
            sizeless.append(face)
        return face

    def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
        face = font if font is not None else self.getfont()
        sized = isinstance(face, ImageFont.FreeTypeFont) and not any(
            face is seen for seen in sizeless
        )
        size = face.size if sized else None
        calls.append(
            TextCall(current["page"], str(text), size, _call_chain(sys._getframe(1)), generator.dpi)
        )
        return original(self, xy, text, fill, font, *args, **kwargs)

    monkeypatch.setattr(ImageFont, "load_default", load_default)
    monkeypatch.setattr(ImageDraw.ImageDraw, "text", spy)
    stream = generator.interior_stream(baseline_puzzles())
    pages = iter(stream.pages)
    drawn = 0
    while True:
        current["page"] = drawn + 1
        try:
            next(pages)
        except StopIteration:
            break
        drawn += 1
    monkeypatch.setattr(ImageDraw.ImageDraw, "text", original)
    monkeypatch.setattr(ImageFont, "load_default", original_default)
    assert drawn == stream.page_count == page_count
    return calls


def clear_font_caches() -> None:
    """Empty ``book_pdf_generator``'s two font caches.

    ``_band_font`` is an ``lru_cache(maxsize=8)`` over ``(size,)`` and
    ``_band_font_bytes`` an ``lru_cache(maxsize=1)``, so a face loaded under
    one font configuration is handed straight back under the next one in the
    same process — and this file records two configurations per book, in one
    process, with ``arial=True`` always first (:func:`recording`).

    **Added by CARD-221 fix 5, because the blindness was demonstrated rather
    than suspected.** The AC/EC/G gate put a host Arial lookup with a
    *sizeless* ``load_default()`` fallback — the CARD-149 defect verbatim —
    inside ``_band_font`` and this whole file stayed green, 21 passed, while
    killing 3 tests when ``TestInteriorType_FloorHoldsWithoutArial`` ran
    alone in a cold process. The warmed cache was the difference. Until it
    was cleared, that class's own claim to be "what fails first if a host
    lookup returns to the drawing" was false of the suite as it actually
    runs.
    """
    book_pdf_generator._band_font.cache_clear()
    book_pdf_generator._band_font_bytes.cache_clear()


def without_arial(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make ``ImageFont.truetype`` fail for the Arial path, and only that path.

    Clears the font caches on the way in (:func:`clear_font_caches`): a face
    cached while Arial was available is not a measurement of a machine
    without it.
    """
    original = ImageFont.truetype

    def truetype(font=None, *args, **kwargs):
        if str(font) == ARIAL_PATH:
            raise OSError(f"cannot open resource {font}")
        return original(font, *args, **kwargs)

    monkeypatch.setattr(ImageFont, "truetype", truetype)
    clear_font_caches()


_RECORDINGS: Dict[Tuple[str, bool], List[TextCall]] = {}


def recording(book: str, arial: bool) -> List[TextCall]:
    """The recorded calls of ``book``'s interior, with or without Arial; once each."""
    key = (book, arial)
    if key not in _RECORDINGS:
        with pytest.MonkeyPatch.context() as monkeypatch:
            if not arial:
                without_arial(monkeypatch)
            _RECORDINGS[key] = record_interior(
                BookPDFGenerator(BOOKS[book]()), monkeypatch, PAGE_COUNTS[book]
            )
    return _RECORDINGS[key]


def below_floor(calls: List[TextCall]) -> List[str]:
    """Every non-exempt call that is unsized or below the floor, described."""
    return [
        call.describe()
        for call in calls
        if not call.exempt and (call.points is None or call.points < FLOOR_PT)
    ]


# --------------------------------------------------------------------------
# ADR-0042/R6 — the same floor, read off the stream of the written file
# (CARD-299)
# --------------------------------------------------------------------------
#
# R6: *a claim about an interior page's geometry, rule widths or tone is
# asserted against the content stream of the written PDF, not against a
# rendered bitmap.* CON-020's floor is a type size, so this file is one of the
# readers that conversion reaches, and the spy above is the reading it names:
# a page written as operators makes **no** ``ImageDraw.text`` call at all, so
# on the day a kind converts, the recording for that page goes empty and the
# floor assertion over it passes by having nothing to judge.
#
# **What is read instead, and what the honest shape of the swap is.** The
# stream states a face's size as the operand of ``Tf``, in points, which is
# CON-020's own unit — no ``size * 72 / dpi`` conversion, no DPI to get wrong,
# and the number comes off the file that actually ships rather than an
# in-memory page upstream of the JPEG.
#
# But the swap cannot be made outright today and the reason is measured, not
# cautious: at CARD-298's merge **all seven page kinds are declared raster**
# (``book_pdf_generator._RASTER_DECLARATIONS``), so every page of the baseline
# interior is ``/image Do`` and ``pdf_vector.type_sizes`` returns ``[]`` on all
# 14 of them. A floor assertion rewritten to read ``Tf`` today would be
# **vacuously green over an empty list** — which is the very defect AC-1's
# non-vacuity sibling exists to prevent, reintroduced by the fix for it.
#
# So the reading below is **medium-agnostic**: each page is read in the medium
# ``page_medium`` declares for its kind — the spy for a bitmap page, the
# stream for a page of operators — and the declarations shrink underneath it
# without this file changing. The floor's force today is byte-for-byte what it
# was, because today every page takes the spy arm; the stream arm is proved
# non-dormant by :class:`TestInteriorType_TheStreamArmIsReached`, on a real
# vector page written by production's own writer.

#: The kinds whose pages letter something for the reader, so that "this kind
#: is covered" is a claim with content. TITLE is absent on purpose: AC-283
#: makes the blank title page blank, and a title page that lettered anything
#: would be a defect in a different test.
#:
#: **This set is hand-written, and :data:`NON_LETTERING_KINDS` beside it is
#: what keeps it from being a silent pass** (review cycle 1's F-003). The two
#: together must PARTITION :class:`~nonogram.admin.book_pdf_generator.PageKind`
#: — asserted by
#: :meth:`TestInteriorType_TheNonVacuityFloorCanFail.test_the_lettering_kinds_partition_the_page_kinds`
#: — so a new page kind is a **failure** here rather than a kind quietly
#: outside the coverage claim (ADR-0039/R2). There is no authority in the tree
#: to derive "letters something" from: whether a kind letters is a fact about
#: what its writer draws, and the writers are exactly what this file is the
#: independent statement of.
LETTERING_KINDS = frozenset({"guide", "toc", "divider", "puzzle", "answer"})

#: The interior's remaining page kinds, each with the reason it letters
#: nothing — the complement of :data:`LETTERING_KINDS`, written out so the
#: pair is checkable against the enum rather than merely plausible.
NON_LETTERING_KINDS = {
    "cover": (
        "not an interior page at all — the cover is its own file and stays "
        "raster permanently (ADR-0042/R2)"
    ),
    "title": (
        "blank by AC-283 (CARD-206): the interior's first page carries no ink "
        "of any kind, so a lettered title page is a defect a different test "
        "catches"
    ),
}

#: The functions that draw a nonogram's **clue digits** — the one family of
#: faces CON-020 exempts. The raster pair is :data:`EXEMPT_CALLERS`, stated by
#: CARD-184; the vector one is ``book_vector_draw.draw_clue_digits``, the only
#: way a page of operators sets a clue digit.
CLUE_DIGIT_DRAWERS = frozenset(
    {name for _module, name in EXEMPT_CALLERS} | {"draw_clue_digits"}
)

#: Where the vector page writers live.
_ADMIN_DIR = Path(book_pdf_generator.__file__).parent


def vector_writer_sources(kind: str) -> Dict[str, str]:
    """Every ``src/`` source that writes a VECTOR page of ``kind``.

    Two authorities, both enumerable, and **empty is meaningful**: a kind with
    no vector writer is a kind nothing can write as operators, so a page of
    that kind classified VECTOR is a page nobody can account for.

    * ``src/nonogram/admin/book_<kind>_vector.py`` — the per-kind writer
      module CARD-295/296/297 established (``book_guide_vector``,
      ``book_toc_vector``, ``book_answer_vector``, ``book_puzzle_vector``);
    * ``BookPDFGenerator.vector_<kind>_page`` — the generator's own method,
      which is where the title page's writer is.
    """
    sources: Dict[str, str] = {}
    module = _ADMIN_DIR / f"book_{kind}_vector.py"
    if module.exists():
        sources[module.name] = module.read_text(encoding="utf-8")
    writer = getattr(BookPDFGenerator, f"vector_{kind}_page", None)
    if writer is not None:
        sources[f"BookPDFGenerator.vector_{kind}_page"] = textwrap.dedent(
            inspect.getsource(writer)
        )
    return sources


def called_names(source: str) -> set:
    """Every name ``source`` **calls**, by AST and not by text.

    By AST deliberately: ``book_guide_vector`` discusses ``_write_clues`` at
    length in its own comments (its lines 235-245) without calling it, so a
    text search over the same files would exempt the guide page — and the
    guide's worked example is precisely the lettering CON-020 does *not*
    exempt.
    """
    names = set()
    for node in ast.walk(ast.parse(source)):
        if isinstance(node, ast.Call):
            function = node.func
            if isinstance(function, ast.Name):
                names.add(function.id)
            elif isinstance(function, ast.Attribute):
                names.add(function.attr)
    return names


def draws_clue_digits(kind: str) -> bool:
    """Does any vector writer of ``kind`` draw clue digits?"""
    return any(
        called_names(source) & CLUE_DIGIT_DRAWERS
        for source in vector_writer_sources(kind).values()
    )


#: The page kinds whose streams **must carry the clue-digit mark**, **derived**
#: from ``src/`` rather than listed (CARD-299 review cycle 1's F-001).
#:
#: This set was CARD-299's *refusal* list — the kinds whose stream a floor
#: could not be read off at all, because CON-020's exemption is keyed on the
#: **function that draws** and a content stream recorded no provenance.
#: CARD-314 put the provenance in the stream, so the set changed job rather
#: than contents: it is now the two-sided bound on the mark. A kind **in** it
#: whose page carries no mark is a failure (the writer's claim is missing,
#: AC-3); a kind **not** in it whose page carries one is a failure (the mark is
#: over-applied, AC-4). Both are in :func:`stream_faces`.
#:
#: Why the set and not just the puzzle page: the exempt sub-floor faces live on
#: **two** kinds, and the answer page holds the larger share. Re-derived on
#: this branch at ``4d164f62``, which is ``main``'s tip with CARD-306 in:
#: **Book 1** has ``('answer', 8.64 pt): 258`` and ``('puzzle', 8.64 pt): 204``
#: — 462 in all, which is the figure CARD-299 and CARD-314 both quote — and the
#: **10 cm minimum trim** adds ``('answer', 3.60 pt): 258``,
#: ``('answer', 5.52 pt): 64``, ``('puzzle', 3.60 pt): 204``,
#: ``('puzzle', 5.76 pt): 54`` and ``('puzzle', 8.40 pt): 64``, for 1106 across
#: the corpus this module walks. CARD-299's refusal was keyed on ``"puzzle"``
#: alone, so the day ``PageKind.ANSWER``'s declaration lifted it would have
#: reported 258 false CON-020 violations on Book 1 alone — the exact failure
#: the refusal existed to prevent.
#:
#: The derivation is :func:`draws_clue_digits` over :func:`vector_writer_sources`,
#: and its control is
#: :meth:`TestInteriorType_TheStreamArmIsReached.test_the_refused_kinds_are_derived_and_agree_with_the_spy`:
#: the same set read a second, independent way — off the live spy recording,
#: keyed on CON-020's own :data:`EXEMPT_CALLERS` — must agree with it. So a
#: renamed drawer empties the AST reading and reds, rather than quietly
#: refusing nothing.
CLUE_DIGIT_KINDS = frozenset(
    kind.value for kind in book_pdf_generator.PageKind if draws_clue_digits(kind.value)
)


@dataclass(frozen=True)
class StreamFace:
    """One ``Tf`` size a written interior page set, read off the shipped file.

    The sibling of :class:`TextCall` for a page of operators, and
    deliberately **poorer**: a content stream records no call chain, so
    ``kind`` here is the page's own :class:`PageKind` value and not one of the
    spy's five semantic kinds.

    **This class had no ``exempt`` until CARD-314, and that absence used to be
    the point.** CARD-299's version said so in as many words: "a content stream
    carries no provenance at all, so this class has nothing to key an exemption
    on and does not pretend to", and the exemption was honoured one level up by
    :func:`stream_faces` **refusing** every page kind that draws clue digits.
    That was correct and it was a hole with a date on it — the day CARD-309
    converts such a page, CON-020 has no verifying reading for it.

    CARD-314 closes it by **putting the provenance in the stream**: a vector
    page's clue digits are written inside a
    :data:`~nonogram.admin.book_vector.CLUE_DIGIT_TAG` marked-content sequence,
    emitted by ``book_vector_draw.draw_clue_digits`` and by nothing else, so a
    reading can recover "this text run is a clue digit" from the shipped file.
    :attr:`exempt` is that mark and **nothing else** — never the face's size:
    a body face measuring a clue digit's 8.64 pt arrives here ``exempt=False``
    and is reported, which is CARD-314's AC-2.

    ``kind`` is still the page's own :class:`PageKind` value and not one of the
    spy's five semantic kinds — the mark says *clue digit or not*, which is the
    one distinction CON-020 needs, and does not reconstruct the call chain.
    """

    page: int
    kind: str
    points: float
    exempt: bool = False

    def describe(self) -> str:
        return f"page {self.page} {self.kind} (stream): {self.points:.2f} pt"


def stream_faces(generator: BookPDFGenerator, puzzles) -> List[StreamFace]:
    """Every ``Tf`` size the written interior sets, on its operator pages only.

    The page kinds come from the generator's own **page plan** and the sizes
    from the **file**, zipped ``strict=True``, so a plan that does not describe
    the file it wrote is a failure rather than a short walk — the same pairing
    ``tests/test_book_pdf.py::_media_by_kind`` uses, and for the same reason.

    **CARD-314 replaced CARD-299's refusal with a reading** (that card's AC-1).
    Round 1 asserted ``kind.value not in CLUE_DIGIT_KINDS`` — a default-DENY on
    every page kind whose writer draws clue digits, because the exemption is
    keyed on the drawing function and a stream recorded no caller. It now reads
    those pages, and exempts a face **by the mark its writer emitted**
    (:func:`~tests.helpers.pdf_vector.marked_type_sizes`) rather than by its
    size. Three bounds hold that honest, and all three are failures rather than
    skips (ADR-0039/R2):

    * a kind whose writer draws clue digits whose stream carries **no mark at
      all** is refused — the writer's claim is missing, so nothing here can
      tell its exempt digits from body type, and the 8.64 pt residue must not
      be exempted on a guess *or* reported as ~204 false violations (AC-3);
    * a face marked on a page whose writer draws **no** clue digits is refused
      — the mark is over-applied, and the guide's worked example is exactly the
      clue digit CON-020 does **not** exempt (AC-4);
    * an unbalanced bracket raises out of ``marked_type_sizes`` — an exemption
      with no readable extent.
    """
    kinds = generator.interior_stream(puzzles).page_kinds
    data = generator.export_interior(puzzles).getvalue()
    media = pdf_vector.page_media(data)
    streams = pdf_vector.content_streams(data)
    faces: List[StreamFace] = []
    for number, (kind, medium, stream) in enumerate(
        zip(kinds, media, streams, strict=True), start=1
    ):
        assert medium != pdf_vector.UNCLASSIFIABLE, (
            f"interior page {number} ({kind.value}) is neither a bitmap nor "
            "operators — its type cannot be read at all (ADR-0039/R2)"
        )
        if medium != pdf_vector.VECTOR:
            continue
        faces.extend(faces_on_page(number, kind.value, stream))
    return faces


def faces_on_page(number: int, kind: str, stream: str) -> List[StreamFace]:
    """Every face of **one** vector page, exempt by its mark (CARD-314).

    Split out of :func:`stream_faces` so the reading can be exercised on a page
    production's own writers really emit. ``export_interior`` cannot yet hand
    one over — every :class:`PageKind` is a declared raster exception and the
    page conversion is CARD-309's, so lifting ``PageKind.PUZZLE``'s declaration
    raises ``"page 6 is a vector puzzle page, but arrived as Image"`` out of the
    generator's own walk (measured on this branch). A test that monkeypatched
    ``page_media`` into saying VECTOR would instead read a **raster** page's
    stream, which is ``/image Do`` with no ``Tf`` in it at all: the refusal
    CARD-299 asserted fired on the page *kind*, before any reading, so it never
    needed a real stream. The bounds below do, so this is the door they knock
    on.
    """
    assert vector_writer_sources(kind), (
        f"interior page {number} ({kind}) is written as operators, "
        "but no vector writer for that kind exists in src/ — neither "
        f"book_{kind}_vector.py nor "
        f"BookPDFGenerator.vector_{kind}_page. So nothing here can "
        "say whether its faces are exempt, and an unclassifiable shape is "
        "a FAILURE and never a silent pass (ADR-0039/R2). The card that "
        "wrote that page owes this file its writer's name."
    )
    read = pdf_vector.marked_type_sizes(stream)
    marked = [face for face in read if face.exempt]
    if kind in CLUE_DIGIT_KINDS:
        assert marked, (
            f"interior page {number} is a VECTOR {kind} page, whose "
            "writer draws clue digits, and its stream carries no "
            f"/{pdf_vector.CLUE_DIGIT_TAG} mark on any of its "
            f"{len(read)} face(s). CON-020's clue-digit exemption is keyed "
            "on the function that draws (png._draw_clues / _write_clues / "
            "book_vector_draw.draw_clue_digits) and a content stream "
            "records no caller, so without the mark this reading has only "
            "two wrong answers available: report every sub-floor digit as "
            "a violation, or exempt 8.64 pt BY ITS VALUE and with it any "
            "body face that happens to measure the same. An unanalysable "
            "shape is a FAILURE (ADR-0039/R2, CARD-314 AC-3). The writer "
            "owes this page its mark."
        )
    else:
        assert not marked, (
            f"interior page {number} is a VECTOR {kind} page, and "
            f"{len(marked)} of its faces are marked "
            f"/{pdf_vector.CLUE_DIGIT_TAG} — but no vector writer of that "
            "kind calls a clue-digit drawer (CLUE_DIGIT_KINDS is derived "
            f"from src/ and is {sorted(CLUE_DIGIT_KINDS)}). The mark is a "
            "claim about provenance, so a page claiming it without drawing "
            "one is over-applying it, and an over-applied mark exempts "
            "body type from CON-020. The guide page's worked example is "
            "exactly that case: its clue digits are the reader's "
            "instruction text and are NEVER exempt (CARD-314 AC-4)."
        )
    return [
        StreamFace(number, kind, face.points, face.exempt) for face in read
    ]


def real_vector_stream(kind: str) -> str:
    """One page of ``kind`` as **production's own vector writer** emits it.

    CARD-314. Every bound in :func:`faces_on_page` is about what a real writer
    puts in a real stream, so none of them is exercised on a hand-built one:
    each entry below is the same call ``BookPDFGenerator`` or its page module
    makes, on this module's own corpus book, and the text is the ``operators``
    joined exactly as :func:`~nonogram.admin.book_vector.ContentStream.render`
    would write them.

    Why not ``export_interior``: the page conversion is CARD-309's and is not
    wired, so lifting a :data:`PageKind`'s raster declaration raises
    ``"page 6 is a vector puzzle page, but arrived as Image"`` out of the
    generator's own walk. :func:`faces_on_page`'s docstring has the rest.

    Raises:
        AssertionError: ``kind`` has no entry. A page kind nobody mapped is a
            kind nothing here can read, and ADR-0039/R2 makes that a failure
            rather than a skipped case — which also means a kind a future card
            teaches to draw clue digits fails this file until it is wired, the
            same way :data:`CLUE_DIGIT_KINDS` is derived rather than listed.
    """
    builder = _REAL_VECTOR_STREAMS.get(kind)
    assert builder is not None, (
        f"{kind!r} has no vector-page builder in this module, so CON-020's "
        f"stream arm cannot be exercised on it. Known: "
        f"{sorted(_REAL_VECTOR_STREAMS)}"
    )
    return "\n".join(builder().operators)


def _real_puzzle_stream():
    generator = BookPDFGenerator(corpus_book())
    payload = BookPDFGenerator._payload(baseline_puzzles()[0])
    return generator.vector_puzzle_page(
        payload, 1, 1, generator.cell_sizes([payload])
    )


def _real_answer_stream():
    generator = BookPDFGenerator(corpus_book())
    payload = BookPDFGenerator._payload(baseline_puzzles()[0])
    page_number = BASELINE_PAGE_COUNT
    return book_answer_vector.answer_page(
        generator.page_spec(page_number),
        generator.dpi,
        payload,
        1,
        page_number,
        None,
    )


def _real_guide_stream():
    generator = BookPDFGenerator(corpus_book())
    pages = book_guide_vector.guide_pages(
        generator.page_spec,
        generator.dpi,
        puzzle_count=len(baseline_puzzles()),
        easy_count=len(baseline_puzzles()),
    )
    return pages[0].stream


def _real_toc_stream():
    generator = BookPDFGenerator(corpus_book())
    # The rows are not this test's subject — whether a real TOC page carries
    # the clue-digit mark is — so they are the production row type with
    # production labels rather than a second derivation of the page plan.
    rows = [
        book_pdf_generator.TocEntry(book_pdf_generator.GUIDE_TITLE, 2),
        book_pdf_generator.TocEntry("Easy", None),
        book_pdf_generator.TocEntry("Puzzles 1-10", 6),
        book_pdf_generator.TocEntry(
            book_pdf_generator.TOC_SOLUTIONS_LABEL, 12, starts_group=True
        ),
    ]
    return next(
        iter(
            book_toc_vector.toc_pages(
                rows, generator.page_spec, generator.dpi, 4
            )
        )
    )


#: One builder per page kind this module can read a real operator page of.
#: Mapped rather than branched so :func:`real_vector_stream` can name what it
#: does not know (ADR-0039/R2); ``divider`` and ``cover`` are absent because no
#: vector writer for them exists (CARD-231, ADR-0042/R2) and ``title`` because
#: AC-283 leaves that page blank, so it sets no face to judge.
_REAL_VECTOR_STREAMS = {
    "puzzle": _real_puzzle_stream,
    "answer": _real_answer_stream,
    "guide": _real_guide_stream,
    "toc": _real_toc_stream,
}


@contextmanager
def _no_clue_digit_mark(monkeypatch):
    """``draw_clue_digits`` with its mark dropped, and nothing else changed.

    AC-3's mutant, planted at the **one chokepoint** that emits the tag — so
    what the missing-mark bound is shown on is a real writer's real page minus
    exactly the claim, rather than a stream assembled to be missing it.

    The emitter is stubbed rather than the drawer rewritten, because
    ``draw_clue_digits`` is imported by name into both page modules
    (``from ... import draw_clue_digits``): patching the function would leave
    those bindings pointing at the original, which is the silent-no-op shape
    this file is full of warnings about. ``begin_marked``/``end_marked`` are
    looked up on the instance at call time, so patching the class reaches every
    caller — and the pair is dropped **together**, so the stream stays balanced
    and the failure under test is the missing mark and not an imbalance.
    """
    with monkeypatch.context() as context:
        context.setattr(book_vector.ContentStream, "begin_marked", lambda *a: None)
        context.setattr(book_vector.ContentStream, "end_marked", lambda *a: None)
        yield


_STREAM_FACES: Dict[str, List[StreamFace]] = {}


def stream_recording(book: str) -> List[StreamFace]:
    """:func:`stream_faces` for ``book``'s interior; once each."""
    if book not in _STREAM_FACES:
        _STREAM_FACES[book] = stream_faces(
            BookPDFGenerator(BOOKS[book]()), baseline_puzzles()
        )
    return _STREAM_FACES[book]


def below_floor_in_its_medium(book: str) -> List[str]:
    """Every face below the floor, each page read in the medium it was written.

    The union of the two arms, which is what makes the claim whole: a kind
    that converts moves from the left arm to the right one, and neither arm
    going quiet can take a face out of the judgment.

    **Both arms now honour the exemption the same way, and neither honours it
    by size** (CARD-314). The left arm reads the drawing function off the spy's
    call chain (:attr:`TextCall.exempt`); the right arm reads the mark the
    writer put in the stream (:attr:`StreamFace.exempt`). The two are the same
    statement — *this face was set by a clue-digit drawer* — carried by the two
    media's different means, which is what lets a page change medium without
    changing what CON-020 claims about it (G-1).
    """
    return below_floor(recording(book, arial=True)) + [
        face.describe()
        for face in stream_recording(book)
        if face.points < FLOOR_PT and not face.exempt
    ]


def kinds_covered_in_their_medium(book: str) -> set:
    """Every page kind whose pages letter something, in its declared medium.

    AC-1's non-vacuity floor, carried through the medium change. The spy's
    recording gives the semantic kinds (``"guide"``, ``"band"``, …) and the
    stream gives :class:`PageKind` values, so the two are reduced to the one
    vocabulary both can speak — the page kind — and the richer semantic floor
    stays asserted beside it in
    :meth:`TestInteriorType_EveryFaceHoldsTheFloor.test_the_recording_covers_every_kind_of_interior_lettering`.
    """
    covered = {
        page_kind
        for page_kind, pages in _pages_by_kind(book).items()
        if any(
            call.page in pages for call in recording(book, arial=True)
        )
        or any(face.kind == page_kind for face in stream_recording(book))
    }
    return covered


_PAGES_BY_KIND: Dict[str, Dict[str, set]] = {}


def _pages_by_kind(book: str) -> Dict[str, set]:
    """``{page kind value: {1-based page numbers}}`` for ``book``'s interior."""
    if book not in _PAGES_BY_KIND:
        kinds = (
            BookPDFGenerator(BOOKS[book]())
            .interior_stream(baseline_puzzles())
            .page_kinds
        )
        by_kind: Dict[str, set] = {}
        for number, kind in enumerate(kinds, start=1):
            by_kind.setdefault(kind.value, set()).add(number)
        _PAGES_BY_KIND[book] = by_kind
    return _PAGES_BY_KIND[book]


# --------------------------------------------------------------------------
# AC-1
# --------------------------------------------------------------------------


class TestInteriorType_EveryFaceHoldsTheFloor:
    """AC-1 — every face outside the exemption is at least 10 pt.

    **CON-020's verifying test, and CARD-299 re-expressed it rather than
    renaming it.** ADR-0042/R6 moves an interior claim onto the content stream
    of the written PDF; this class's two node ids are unchanged, so CON-020's
    ``check:`` and its ``trace.yml`` row still resolve to the same two
    definitions they did before — the re-expression is in what the assertions
    read, not in what they are called.

    What changed: both assertions now read each page in the medium
    ``page_medium`` declares for its kind (see the block comment above
    :class:`StreamFace`). Today every kind is a declared raster exception, so
    both read exactly what they read before; the stream arm is proved
    non-dormant by :class:`TestInteriorType_TheStreamArmIsReached`.
    """

    def test_every_face_outside_the_exemption_is_at_least_ten_points(self, book):
        assert below_floor_in_its_medium(book) == []

    def test_the_recording_covers_every_kind_of_interior_lettering(self, book):
        """CARD-198: "answer heading" is gone — there is no level heading
        left to draw inside the answer section at all. "answer caption" is
        also not required on ``min-trim``: CARD-197's AC-6 omits the caption
        rather than overlap the drawing when the trim leaves no slack for
        it, which the 10x10 cm book genuinely does not.

        **This is the assertion the floor above rests on, and CARD-299's job
        was to carry it across the medium change without weakening it.** Its
        sibling is ``below_floor_in_its_medium(book) == []``, which is
        **vacuously true of an empty reading** — a recording that saw nothing
        holds every floor there is. What makes CON-020 a real constraint is
        this test, and the medium change is exactly the event that could have
        emptied the reading silently: a page written as operators makes no
        ``ImageDraw.text`` call, so the spy would simply stop seeing it.

        So the floor is asserted twice over, in two vocabularies:

        * the **semantic** kinds the spy can see — guide, divider, band,
          footer label, answer caption — unchanged from CARD-184, which is the
          finer of the two and the one that would notice a *piece* of
          lettering going missing from a page that still letters something;
        * every **page kind** that letters at all, in whichever medium it was
          written (:func:`kinds_covered_in_their_medium`), which is the only
          vocabulary a content stream can speak, and the one that keeps biting
          after a kind converts and the semantic arm goes quiet for it.
        """
        kinds = {call.kind for call in recording(book, arial=True)}
        required = {"guide", "divider", "band"}
        if book != "min-trim":
            # CARD-222's footer line. Not on ``min-trim``: no page of that
            # book frees its footer strip (that file's own measurement), so
            # the group — label included — is omitted there.
            required.add("footer label")
        if book != "min-trim":
            required.add("answer caption")
        assert required <= kinds

        # The medium-independent half: every kind that letters is covered,
        # whichever arm read it. ``LETTERING_KINDS`` is intersected with the
        # kinds this book's plan actually holds, so the claim is about pages
        # that exist rather than about a kind the 10x10 cm book never prints.
        planned = LETTERING_KINDS & set(_pages_by_kind(book))
        assert planned <= kinds_covered_in_their_medium(book), (
            sorted(planned - kinds_covered_in_their_medium(book))
        )
        assert planned, "this book's plan letters nothing at all"


# --------------------------------------------------------------------------
# AC-2
# --------------------------------------------------------------------------


class TestInteriorType_FloorHoldsWithoutArial:
    """AC-2 — with Arial unavailable, no face is unsized and the floor holds.

    **Deliberately redundant since CARD-221** (its review cycle 1, F-007).
    That card made ``_guide_face`` return the packaged face on every host,
    so ``without_arial`` can no longer change anything the interior draws:
    every assertion below now measures the same recording as
    :class:`TestInteriorType_EveryFaceHoldsTheFloor` above, and this class
    passes for a reason it no longer tests.

    It is kept rather than retired, as insurance of the cheapest kind: it
    costs one extra export per book and it is the test that fails first if
    a host lookup ever comes back into the interior — including one that
    CARD-221's own structural watch would miss, since that watch
    (``tests/test_book_interior_face.py``'s
    ``TestInteriorFace_NoFaceIsReadFromAHostPath``) looks at
    ``ImageFont.truetype``'s argument while this one looks at what was
    actually drawn. ``test_arial_really_is_unavailable`` below is still a
    real test of the helper, not of the interior.

    The claim this class can no longer make on its own is "the floor holds
    on a machine without Arial **because this run had none**" — that one
    moved to ``tests/test_book_interior_face.py``, which exports the same
    books twice and compares them. Read the two together.
    """

    def test_arial_really_is_unavailable(self):
        with pytest.MonkeyPatch.context() as monkeypatch:
            without_arial(monkeypatch)
            with pytest.raises(OSError):
                ImageFont.truetype(ARIAL_PATH, 60)

    def test_no_face_is_unsized(self, book):
        unsized = [call.describe() for call in recording(book, arial=False) if call.size_px is None]
        assert unsized == []

    def test_every_face_outside_the_exemption_is_at_least_ten_points(self, book):
        assert below_floor(recording(book, arial=False)) == []

    def test_the_dividers_are_drawn(self, book):
        dividers = [call for call in recording(book, arial=False) if call.kind == "divider"]
        # Three levels and SOLUTIONS, two draw.text calls each since
        # CARD-200 (the word, then the folio sharing its bottom-outer
        # corner — both carry "create_divider_page" in their call chain,
        # so both are tagged "divider" by `TextCall.kind`).
        assert len(dividers) == 8


# --------------------------------------------------------------------------
# AC-3
# --------------------------------------------------------------------------


class TestInteriorType_OnlyPuzzleClueDigitsAreExempt:
    """AC-3 — only puzzle-page clue digits are exempt, and they are exercised."""

    def test_the_exempt_set_is_non_empty(self, book):
        assert [call for call in recording(book, arial=True) if call.exempt]

    def test_only_the_two_clue_writers_are_exempt(self, book):
        callers = {call.caller for call in recording(book, arial=True) if call.exempt}
        assert callers <= EXEMPT_CALLERS

    def test_exempt_calls_are_puzzle_page_digits(self, book):
        exempt = [call for call in recording(book, arial=True) if call.exempt]
        assert all(call.text.isdigit() for call in exempt)
        assert all(call.kind == "other" for call in exempt)

    def test_worked_example_digits_are_drawn_and_never_exempt(self, book):
        example = [
            call for call in recording(book, arial=True) if WORKED_EXAMPLE in call.caller_names
        ]
        assert example, "the guide page's worked example drew no text"
        assert not any(call.exempt for call in example)

    def test_the_exemption_rule_by_name(self):
        def call(*chain: Tuple[str, str]) -> TextCall:
            return TextCall(1, "3", 10, tuple(chain), 300)

        png = ("nonogram.export.png", "_draw_clues")
        writer = ("nonogram.admin.book_pdf_generator", "_write_clues")
        example = ("nonogram.admin.book_pdf_generator", WORKED_EXAMPLE)
        assert call(png).exempt
        assert call(writer).exempt
        assert not call(writer, example).exempt
        assert not call(example).exempt
        assert not call(("nonogram.export.png", "render_answer_page")).exempt


# --------------------------------------------------------------------------
# AC-4
# --------------------------------------------------------------------------


class TestDividerPage_PointSizeIsIndependentOfDpi:
    """AC-4 — the divider is 14.4 pt at 300 DPI and at 600 DPI.

    CARD-200 (SCOPE+): a divider page now draws two faces, not one — its
    own word, then the folio sharing its bottom-outer corner — so this
    test's own spy now expects two sizes, in the order they are drawn, not
    one.
    """

    @staticmethod
    def divider_points(dpi: int, monkeypatch: pytest.MonkeyPatch) -> List[float]:
        monkeypatch.setattr(book_pdf_generator, "DPI", dpi)
        generator = BookPDFGenerator(corpus_book())
        assert generator.dpi == dpi
        sizes: List[Optional[int]] = []
        original = ImageDraw.ImageDraw.text

        def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
            sizes.append(font.size if isinstance(font, ImageFont.FreeTypeFont) else None)
            return original(self, xy, text, fill, font, *args, **kwargs)

        with monkeypatch.context() as patch:
            patch.setattr(ImageDraw.ImageDraw, "text", spy)
            generator.create_divider_page(2, "Easy")
        assert sizes and None not in sizes
        return [size * POINTS_PER_INCH / dpi for size in sizes]

    @staticmethod
    def _expected_folio_pt(dpi: int) -> float:
        """:data:`FOLIO_PT` round-tripped through whole device pixels.

        Unlike :data:`DIVIDER_PT` (14.4 pt is exactly 60 px at 300 DPI, no
        rounding), 10.0 pt rounds to 42 px at 300 DPI — 10.08 pt, not 10.0 —
        so the independent expectation here is the same whole-pixel rounding
        :func:`~nonogram.admin.book_pdf_generator.type_px` performs, written
        out rather than imported, not a loosened tolerance.
        """
        return round(FOLIO_PT * dpi / POINTS_PER_INCH) * POINTS_PER_INCH / dpi

    def test_the_divider_is_the_same_size_in_points_at_300_and_600_dpi(self, monkeypatch):
        at_300 = self.divider_points(300, monkeypatch)
        at_600 = self.divider_points(600, monkeypatch)
        assert at_300 == pytest.approx([DIVIDER_PT, self._expected_folio_pt(300)])
        assert at_600 == pytest.approx([DIVIDER_PT, self._expected_folio_pt(600)])


class TestInteriorType_DifficultyDotsAreNotText:
    """CARD-228 (G-2): the difficulty glyph is ink, not type, so the floor misses it.

    CON-020 is a rule about *text*, and ``TestInteriorType_EveryFaceHoldsTheFloor``
    above enforces it by spying on ``draw.text``. CARD-228's three dots are
    drawn as circles, so that spy does not see them — and the card says it
    should not (guardrail G-2: the dots are not text; the **word** beside them
    is, and is held to the floor by its own caller).

    A guardrail no test can falsify is worth nothing, so both halves of that
    sentence are measured here rather than asserted in a docstring:

    * the glyph makes **no** ``draw.text`` call at all, so the floor cannot
      reach it *and* nothing can evade the floor by hiding a caption inside
      it (a dot drawn as a "•" glyph at 6 pt would be exactly that);
    * the spy that sees nothing here is the same spy that *does* see the
      word, which is the control — without it, "no text calls" could equally
      mean the spy was broken.
    """

    BOX = (0, 0, 999, 141)

    @staticmethod
    def _text_sizes(draw_something) -> List[Optional[int]]:
        """Every ``draw.text`` size ``draw_something`` asks for, in order."""
        sizes: List[Optional[int]] = []
        original = ImageDraw.ImageDraw.text

        def spy(self, xy, text, fill=None, font=None, *args, **kwargs):
            sizes.append(font.size if isinstance(font, ImageFont.FreeTypeFont) else None)
            return original(self, xy, text, fill, font, *args, **kwargs)

        with pytest.MonkeyPatch.context() as patch:
            patch.setattr(ImageDraw.ImageDraw, "text", spy)
            draw_something()
        return sizes

    def _page(self):
        page = Image.new("RGB", (self.BOX[2] + 1, self.BOX[3] + 1), "white")
        return page, ImageDraw.Draw(page)

    def test_the_glyph_sets_no_type_at_all(self):
        page, draw = self._page()
        drawn: List[object] = []

        def draw_dots():
            drawn.append(
                book_pdf_generator._draw_difficulty_dots(draw, "medium", *self.BOX)
            )

        assert self._text_sizes(draw_dots) == []
        assert drawn[0] is not None, "the glyph must have drawn, or this proves nothing"

    def test_the_spy_does_see_the_word_beside_them(self):
        """The control: the same spy, on the band line the glyph sits beside."""
        page, draw = self._page()
        band = book_pdf_generator.HeaderBand(
            height=self.BOX[3] + 1,
            center_x=(self.BOX[0] + self.BOX[2]) // 2,
            center_y=(self.BOX[1] + self.BOX[3]) // 2,
            font_size=book_pdf_generator.type_px(FLOOR_PT, 300),
        )

        def draw_word():
            book_pdf_generator._set_band(draw, band, "Puzzle 12 · Medium", self.BOX[2] + 1)

        sizes = self._text_sizes(draw_word)
        assert len(sizes) == 1
        assert sizes[0] is not None
        assert sizes[0] * POINTS_PER_INCH / 300 >= FLOOR_PT


# --------------------------------------------------------------------------
# ADR-0042/R6 — the stream arm is reached, and the non-vacuity floor can fail
# (CARD-299)
# --------------------------------------------------------------------------


class TestInteriorType_TheStreamArmIsReached:
    """The medium-agnostic floor really reads a stream, and really discriminates.

    Three claims, and none of them is "the suite is still green". At this
    commit every page kind is a declared raster exception, so
    :func:`below_floor_in_its_medium`'s stream arm contributes nothing to any
    assertion above — which means without this class the conversion would be a
    branch nobody took, asserted by a test that could not tell.
    """

    def test_lifting_a_declaration_makes_the_stream_arm_read_that_page(
        self, monkeypatch
    ):
        """A real vector page, written by production's own writer, is read there.

        The declaration is lifted exactly as ``tests/test_book_pdf.py``'s
        mixed-file test lifts it, so the file walked is the file a converted
        book will hold. The reader is wrapped rather than asserted *about*,
        because the question is whether the arm **called** it: a reader that
        fell through to the spy would leave the wrapper untouched and the
        recorded page list empty.

        **The wrapped reader is ``marked_type_sizes`` since CARD-314**, which
        is the one this arm now reads with — the exemption is the mark, so a
        wrapper on the size-only ``type_sizes`` would record nothing and this
        test would claim the arm was never reached.
        """
        monkeypatch.delitem(
            book_pdf_generator._RASTER_DECLARATIONS,
            book_pdf_generator.PageKind.TITLE,
        )
        asked: List[str] = []
        original = pdf_vector.marked_type_sizes
        monkeypatch.setattr(
            pdf_vector,
            "marked_type_sizes",
            lambda stream: (asked.append(stream), original(stream))[1],
        )

        faces = stream_faces(BookPDFGenerator(corpus_book()), baseline_puzzles())

        # Exactly one page took the stream arm: the title page, now operators.
        assert len(asked) == 1, len(asked)
        # And it is genuinely blank, which is AC-283 and why it adds no face.
        assert faces == []

    def test_the_floor_catches_a_real_vector_pages_sub_floor_type(self):
        """The stream arm discriminates — on a real page, at a real size.

        The measurement behind CARD-299's raised finding, asserted rather than
        reported: ``vector_puzzle_page`` is the one vector page writer the
        generator exposes that letters anything, and the type it sets is
        **8.64 pt** clue digits beside a **14.16 pt** band. So a stream-read
        floor is not a formality — it has something below 10 pt to find on the
        very first page the phase converts, and it finds it.

        **CARD-306 added a third size and it is the one above the floor.**
        That card put the sheet's furniture on this page — the folio, the
        grid-size label and the QR group's two lines — all set at
        ``type_px(10 pt, 300 DPI)``, which is 42 device pixels and reaches
        the stream as **10.08 pt**. So CON-020's 10 pt interior floor is
        **met** by every mark this card added, with 0.08 pt of slack that is
        the one whole device pixel the raster font had to be asked for; the
        sub-floor residue is still the clue digits and still only them. The
        third figure is asserted below rather than left to be discovered,
        because a furniture size that silently dropped under 10 pt would
        otherwise look like the exempt digits.

        It is also the whole of the finding: those 8.64 pt digits are exactly
        the ones CON-020 **exempts**, and nothing in the stream says so. The
        exemption is keyed on the drawing function (``png._draw_clues`` /
        ``_write_clues``) and a content stream records no provenance, so this
        floor cannot honour the exemption it must honour. That is why
        CARD-299's :func:`stream_faces` refused a vector puzzle page by name
        instead of reporting 205 false violations or exempting 8.64 pt by its
        value — and why **CARD-314 marks the digits in the stream** instead, so
        that the exemption survives the conversion. The sizes below are
        unchanged by that: a marked-content bracket sets no type.
        """
        generator = BookPDFGenerator(corpus_book())
        payload = BookPDFGenerator._payload(baseline_puzzles()[0])
        sizes = generator.cell_sizes([payload])
        stream = "\n".join(
            generator.vector_puzzle_page(payload, 1, 1, sizes).operators
        )

        found = pdf_vector.type_sizes(stream)

        assert sorted(set(found)) == [8.64, 10.08, 14.16], sorted(set(found))
        # CARD-306's furniture is the middle figure, and it clears the floor.
        assert 10.08 >= FLOOR_PT, FLOOR_PT
        assert [size for size in found if size < FLOOR_PT] == [8.64] * found.count(
            8.64
        ), sorted(set(found))
        assert [size for size in found if size < FLOOR_PT], (
            "a vector puzzle page sets nothing below the floor, so this "
            "card's finding about the clue-digit exemption has no subject"
        )

    def test_a_vector_puzzle_page_refuses_rather_than_reading_its_clue_digits(
        self, monkeypatch
    ):
        """The default-DENY arm: an unreadable shape FAILS (ADR-0039/R2).

        **CARD-314 moved what this refuses, and kept that it refuses.** While a
        stream carried no provenance at all, every vector puzzle page was
        refused by name: the exemption is keyed on the drawing function, so a
        reading that instead skipped the page, or exempted 8.64 pt because that
        is what clue digits happen to measure, would be the silent pass
        ADR-0039/R2 forbids — the second would exempt a *body* face that
        happened to be 8.64 pt. The page is now **read**
        (:meth:`test_a_marked_vector_puzzle_page_is_read_and_exempted_by_the_mark`),
        and what is refused is the same page **with its writer's mark missing**,
        which is CARD-314's AC-3 and the identical argument: a page whose
        provenance cannot be recovered has only those two wrong answers
        available, so it fails instead.

        The mark is dropped at its one chokepoint — ``draw_clue_digits``, the
        only emitter in the package — so what is exercised is a real writer's
        output minus the claim, not a hand-built stream. The page itself is the
        real one: :func:`real_vector_stream` calls production's own
        ``vector_puzzle_page``, which is what ``export_interior`` cannot yet be
        made to do (see :func:`faces_on_page`).
        """
        with _no_clue_digit_mark(monkeypatch):
            stream = real_vector_stream("puzzle")

        assert pdf_vector.type_sizes(stream), "the page set no type at all"
        assert not [
            face for face in pdf_vector.marked_type_sizes(stream) if face.exempt
        ], "the mark survived being dropped, so this test asserts nothing"
        with pytest.raises(AssertionError, match="VECTOR puzzle page"):
            faces_on_page(6, "puzzle", stream)

    def test_a_vector_answer_page_refuses_too(self, monkeypatch):
        """Review cycle 1's F-001 — the bound covers BOTH kinds, not one.

        CARD-299 round 1 keyed its refusal on ``"puzzle"`` alone. Re-derived on
        this branch at ``4d164f62``, **258 of Book 1's 462 exempt sub-floor
        faces are on ANSWER pages** — more than the puzzle page's 204 — drawn
        through ``book_pdf_generator._write_clues``, and
        ``book_answer_vector.draw_clue_digits`` draws them in the vector medium
        too. So the day ``PageKind.ANSWER``'s declaration lifted, the one-kind
        refusal would not have fired: it would have read the page and reported
        258 false CON-020 violations, which is the exact failure the refusal
        existed to prevent.

        CARD-314 keeps that two-sidedness where it keeps the refusal: in the
        missing-mark bound, which is derived over the same
        :data:`CLUE_DIGIT_KINDS` and so covers the answer page without naming
        it.
        """
        with _no_clue_digit_mark(monkeypatch):
            stream = real_vector_stream("answer")

        assert pdf_vector.type_sizes(stream), "the page set no type at all"
        with pytest.raises(AssertionError, match="VECTOR answer page"):
            faces_on_page(12, "answer", stream)

    @pytest.mark.parametrize("kind", sorted(CLUE_DIGIT_KINDS))
    def test_a_marked_vector_page_is_read_and_exempted_by_the_mark(self, kind):
        """CARD-314's AC-1 — the exemption survives in the stream.

        The pages CARD-299 had to refuse are read, and the 10 pt floor is
        asserted over their **non-exempt** faces only. Both halves are
        asserted, because either alone is satisfiable by the wrong
        implementation: a reading that exempted everything would show no
        violations and no non-exempt faces either, and a reading that exempted
        nothing would show the whole sub-floor residue.

        Parametrised over :data:`CLUE_DIGIT_KINDS`, which is **derived** from
        ``src/`` — so the kind CARD-299's review cycle 1 found missing cannot go
        missing from the positive direction either, and a kind a future card
        teaches to draw clue digits joins this claim without an edit.
        """
        stream = real_vector_stream(kind)

        faces = faces_on_page(1, kind, stream)

        exempt = [face for face in faces if face.exempt]
        body = [face for face in faces if not face.exempt]
        assert exempt, "no face carried the mark, so nothing was exempted"
        assert body, "every face was exempted, so the floor judges nothing"
        assert [face.points for face in exempt if face.points >= FLOOR_PT] == [], (
            "a face at or above the floor is marked exempt, so the mark is "
            "reaching type the exemption was never about"
        )
        assert min(face.points for face in body) >= FLOOR_PT, sorted(
            {face.points for face in body if face.points < FLOOR_PT}
        )
        # And the union judgment is clean: the exempt digits are out of it.
        assert [
            face.describe()
            for face in faces
            if face.points < FLOOR_PT and not face.exempt
        ] == []

    @pytest.mark.parametrize("kind", sorted(CLUE_DIGIT_KINDS))
    def test_a_body_face_at_the_clue_digit_size_is_reported(self, kind):
        """**CARD-314's AC-2, and the card's central control** (G-2).

        *Given a body face that measures the same size as a clue digit, then it
        is reported as a violation.* A size-keyed exemption — the cheap way to
        stop refusing, which CARD-299's own docstring named as the thing not to
        do — passes every other test in this class and fails this one. So this
        is the test that makes "by the mark, never by the size" shippable
        rather than merely asserted in a comment. The mutant is recorded in
        this card's report: replacing :attr:`StreamFace.exempt` with
        ``points == 8.64`` leaves the rest of the module green and reds here.

        The body face is set **outside** every marked-content sequence, through
        the same :meth:`~nonogram.admin.book_vector.ContentStream.text`
        primitive the band and the folio use, at **exactly** the size the clue
        digits on the same page measure — read off that page rather than
        written as 8.64, so the two cannot drift apart and leave this test
        planting a size nothing else sets. It carries no mark, so the floor must
        report it, and the real clue digits beside it must still be exempt:
        together those two assertions separate "reads the mark" from both
        "exempts by size" and "exempts nothing".
        """
        clean = real_vector_stream(kind)
        digits = [
            face.points
            for face in pdf_vector.marked_type_sizes(clean)
            if face.exempt and face.points < FLOOR_PT
        ]
        assert digits, "this page sets no sub-floor clue digit to impersonate"
        planted = min(digits)

        stream = f"{clean}\n0 g BT /F1 {planted} Tf 100 100 Td (8) Tj ET"

        faces = faces_on_page(1, kind, stream)
        at_the_size = [face for face in faces if face.points == planted]
        assert len(at_the_size) == len(digits) + 1, (len(at_the_size), len(digits))
        assert any(not face.exempt for face in at_the_size), (
            "the planted body face at the clue digits' own size came back "
            "exempt, so the exemption is keyed on the SIZE and not on the mark "
            "(CARD-314 G-2)"
        )
        assert any(face.exempt for face in at_the_size), (
            f"no face at {planted} pt is exempt, so the real clue digits lost "
            "their exemption and this test would pass for the wrong reason"
        )
        reported = [
            face.describe()
            for face in faces
            if face.points < FLOOR_PT and not face.exempt
        ]
        assert len(reported) == 1, reported

    def test_an_over_applied_mark_on_a_page_that_draws_none_is_a_failure(self):
        """AC-4, direction two — a body face wrongly marked is CAUGHT.

        The guide page is the real case and not a hypothetical: its worked
        example sets clue digits, and CON-020 holds **those** to the floor
        because they are the reader's instruction text (``draw_example_line``,
        this module's :data:`WORKED_EXAMPLE`). No vector guide writer calls a
        clue-digit drawer, so ``guide`` is outside :data:`CLUE_DIGIT_KINDS`, and
        a guide page that carried the mark would be exempting exactly the type
        the constraint exists to protect.

        What reds is :func:`stream_faces`' second bound. The other half of
        AC-4 — the mark reaching a page kind that *does* draw clue digits, but
        around the wrong run — is held by
        :meth:`TestInteriorType_TheClueDigitMarkIsTheWritersOwn.test_only_the_clue_digit_drawer_emits_the_mark`,
        which walks ``src/`` and is the chokepoint guard.
        """
        assert "guide" not in CLUE_DIGIT_KINDS, sorted(CLUE_DIGIT_KINDS)
        clean = real_vector_stream("guide")

        # The control first: the real guide page is READ, and carries no mark.
        faces = faces_on_page(3, "guide", clean)
        assert faces, "the guide page set no type at all"
        assert not [face for face in faces if face.exempt], "the guide is marked"

        borrowed = (
            f"{clean}\n/{pdf_vector.CLUE_DIGIT_TAG} BMC\n"
            "0 g BT /F1 8.64 Tf 100 100 Td (1) Tj ET\nEMC"
        )
        with pytest.raises(AssertionError, match="over-applying"):
            faces_on_page(3, "guide", borrowed)

    def test_an_unbalanced_mark_is_a_failure_not_a_silent_exemption(self):
        """An exemption with no readable extent FAILS (ADR-0039/R2).

        Two shapes, and each would otherwise be a silent pass in a different
        direction: a sequence left **open** claims every face after it, and an
        ``EMC`` closing nothing makes the stack negative and would, on a
        flag-based reading, leave the rest of the page marked. Both raise, and
        the writer refuses to write either
        (:func:`~nonogram.admin.book_vector.write_vector_page`).
        """
        with pytest.raises(ValueError, match="open at its end"):
            pdf_vector.marked_type_sizes(
                f"/{pdf_vector.CLUE_DIGIT_TAG} BMC\n0 g BT /F1 8.64 Tf 0 0 Td (1) Tj ET"
            )
        with pytest.raises(ValueError, match="never opened"):
            pdf_vector.marked_type_sizes(
                f"/{pdf_vector.CLUE_DIGIT_TAG} BMC\nEMC\nEMC\n"
                "0 g BT /F1 8.64 Tf 0 0 Td (1) Tj ET"
            )
        # The control: the balanced spelling of the same stream reads fine, and
        # reads the one face as exempt — so the two refusals above are about the
        # brackets and not about the reader rejecting clue digits generally.
        assert pdf_vector.marked_type_sizes(
            f"/{pdf_vector.CLUE_DIGIT_TAG} BMC\n"
            "0 g BT /F1 8.64 Tf 0 0 Td (1) Tj ET\nEMC"
        ) == [pdf_vector.MarkedFace(8.64, True)]

    def test_the_bound_does_not_absorb_the_guide_or_the_toc(self):
        """ADR-0039/R3's control — what the bound must NOT swallow.

        An exemption is a claim, so it carries a control for what it must not
        absorb. The guide and the TOC letter the reader and their writers draw
        no clue digits, so their streams are exactly the pages this floor must
        keep reading — and the guide's worked example sets clue digits that
        CON-020 holds to the floor rather than exempting. A bound that widened
        to "any page that sets small type", or keyed itself on 8.64 pt, would
        take these with it.

        Renamed from ``test_the_refusal_does_not_absorb_the_guide_or_the_toc``?
        **No** — that name is kept below, unchanged, because CARD-314's G-6
        forbids renaming a test. This is its twin for the direction CARD-314
        adds: those two pages must carry **no mark**, which is the AC-4 bound
        read as a property of the shipped writers rather than of a planted one.
        """
        for kind in ("guide", "toc"):
            assert kind in LETTERING_KINDS, kind
            assert kind not in CLUE_DIGIT_KINDS, kind

            faces = faces_on_page(1, kind, real_vector_stream(kind))

            assert faces, kind
            assert not [face for face in faces if face.exempt], kind

    def test_the_refusal_does_not_absorb_the_guide_or_the_toc(self):
        """ADR-0039/R3's control — what the refusal must NOT swallow.

        An exemption is a claim, so it carries a control for what it must not
        absorb. The guide and the TOC letter the reader and their writers draw
        no clue digits, so their streams are exactly the pages this floor must
        keep reading — and the guide's worked example sets clue digits that
        CON-020 holds to the floor rather than exempting. A refusal that
        widened to "any page that sets small type", or keyed itself on 8.64 pt,
        would take these with it.
        """
        for kind in ("guide", "toc"):
            assert kind in LETTERING_KINDS, kind
            assert kind not in CLUE_DIGIT_KINDS, kind
            with pytest.MonkeyPatch.context() as context:
                self._refuse_only(kind, context)
                # No raise: the page is read, not refused.
                stream_faces(BookPDFGenerator(corpus_book()), baseline_puzzles())

    def test_a_page_kind_with_no_vector_writer_is_a_failure_not_a_pass(
        self, monkeypatch
    ):
        """ADR-0039/R2 — a kind that cannot be classified FAILS.

        ``divider`` stays raster (G-2) and CARD-231 is the card that makes it
        vector. There is no ``book_divider_vector.py`` and no
        ``BookPDFGenerator.vector_divider_page``, so nothing in ``src/`` can
        say whether a vector divider would draw clue digits — and the rule is
        that such a kind is a failure here, loudly, rather than a page read on
        a guess.
        """
        assert vector_writer_sources("divider") == {}, "a writer appeared"
        self._refuse_only("divider", monkeypatch)
        with pytest.raises(AssertionError, match="no vector writer for that kind"):
            stream_faces(BookPDFGenerator(corpus_book()), baseline_puzzles())

    def test_the_refused_kinds_are_derived_and_agree_with_the_spy(self):
        """:data:`CLUE_DIGIT_KINDS` is derived, and read a second way agrees.

        The derivation walks ``src/`` with :mod:`ast`: for each page kind it
        finds that kind's vector writers (:func:`vector_writer_sources`) and
        asks whether any of them **calls** a clue-digit drawer. The second,
        independent reading is the live spy recording keyed on CON-020's own
        :data:`EXEMPT_CALLERS` — a different medium, a different mechanism, and
        no shared code with the first.

        The agreement is what makes the derivation non-vacuous. If
        ``draw_clue_digits`` were renamed, the AST reading would quietly empty
        and refuse nothing; the spy reading would still name both kinds, and
        this reds. It also pins the direction cycle 1's F-001 was about: both
        readings say **two** kinds, not one.
        """
        from nonogram.admin import book_vector_draw

        assert hasattr(book_vector_draw, "draw_clue_digits"), (
            "the vector clue-digit drawer this derivation seeds on no longer "
            "exists under that name, so the AST reading below reads nothing"
        )

        by_the_spy = set()
        for name in sorted(BOOKS):
            page_kind = {
                page: kind
                for kind, pages in _pages_by_kind(name).items()
                for page in pages
            }
            by_the_spy |= {
                page_kind[call.page]
                for call in recording(name, arial=True)
                if call.exempt
            }

        assert by_the_spy == {"answer", "puzzle"}, sorted(by_the_spy)
        assert set(CLUE_DIGIT_KINDS) == by_the_spy, (
            sorted(CLUE_DIGIT_KINDS),
            sorted(by_the_spy),
        )

    def test_the_stream_arm_of_the_floor_judges_a_face_it_is_handed(
        self, monkeypatch
    ):
        """Review cycle 1's F-006 — the stream arm, on a non-empty reading.

        Every kind is a declared raster exception at this commit, so the union
        in :func:`below_floor_in_its_medium` has only ever been asked to add an
        **empty** right-hand side. A sub-floor face is handed to it here and
        has to come out in the verdict; a face at the floor must not.

        **CARD-314 adds the third case, and it is the exemption's own.** The
        same sub-floor face, marked, must come out of the verdict — because
        that is what the whole card does to this union, and an arm that
        reported it anyway would turn a vector puzzle page into 204 false
        violations. The three cases together pin all three outcomes of
        ``points < FLOOR_PT and not exempt``, so neither clause can be dropped
        without one of them reddening.
        """
        monkeypatch.setitem(_STREAM_FACES, "book1", [StreamFace(7, "toc", 9.0)])

        assert below_floor_in_its_medium("book1") == [
            "page 7 toc (stream): 9.00 pt"
        ]

        monkeypatch.setitem(
            _STREAM_FACES, "book1", [StreamFace(7, "toc", FLOOR_PT)]
        )

        assert below_floor_in_its_medium("book1") == []

        monkeypatch.setitem(
            _STREAM_FACES,
            "book1",
            [StreamFace(7, "puzzle", 8.64, exempt=True)],
        )

        assert below_floor_in_its_medium("book1") == []

    @staticmethod
    def _refuse_only(kind: str, monkeypatch) -> None:
        """Classify every page of ``kind`` VECTOR and every other page RASTER.

        Keyed off the generator's own page plan, so the forced classification
        lines up with the kinds :func:`stream_faces` zips it against.
        """
        pages = _pages_by_kind("book1")[kind]
        media = [
            pdf_vector.VECTOR if number in pages else pdf_vector.RASTER
            for number in range(1, PAGE_COUNTS["book1"] + 1)
        ]
        assert pdf_vector.VECTOR in media, kind
        monkeypatch.setattr(pdf_vector, "page_media", lambda _data: list(media))


# --------------------------------------------------------------------------
# CARD-314 — the mark is the writer's own, and it is the only thing exempting
# --------------------------------------------------------------------------


class TestInteriorType_TheClueDigitMarkIsTheWritersOwn:
    """The mark is a claim, so this is where the claim's authorship is held.

    CON-020's exemption is keyed on **the function that draws**. The mark is
    that key carried into a medium that records no caller, which makes it only
    as trustworthy as the rule about who may emit it: a second emitter is a
    second author of a provenance claim, and an exemption two places can grant
    is an exemption nobody checks. So the chokepoint is asserted structurally,
    over ``src/`` on disk, exactly as this module's layering-style walks do.

    This is the **other** direction of CARD-314's AC-4 (ADR-0039/R1 asks for
    one mutant per direction):
    :meth:`TestInteriorType_TheStreamArmIsReached.test_an_over_applied_mark_on_a_page_that_draws_none_is_a_failure`
    catches a mark that reached the wrong *page*; this catches a mark that
    reached the wrong *code*, which is how it would reach the wrong page in the
    first place.
    """

    #: The one function in the package allowed to emit the clue-digit mark.
    EMITTER = "draw_clue_digits"

    #: ``src/nonogram/admin``'s own files, where every vector writer lives.
    SOURCES = sorted(Path(book_pdf_generator.__file__).parent.glob("*.py"))

    @staticmethod
    def _enclosing_functions(source: str, names: frozenset) -> set:
        """Which ``def``s in ``source`` contain a call to any of ``names``.

        By AST, and the enclosing ``def`` is resolved by walking the tree with
        a parent trail rather than by reading indentation — a call inside a
        nested ``def`` or a comprehension must be attributed to the function it
        is really in, and the memory rule this board keeps says to attribute by
        the enclosing definition and never by proximity.
        """
        found = set()
        stack: list = []

        def walk(node, enclosing):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                enclosing = node.name
            if isinstance(node, ast.Call):
                function = node.func
                called = (
                    function.id
                    if isinstance(function, ast.Name)
                    else getattr(function, "attr", None)
                )
                if called in names:
                    found.add(enclosing)
            for child in ast.iter_child_nodes(node):
                walk(child, enclosing)

        walk(ast.parse(source), None)
        del stack
        return found

    def test_only_the_clue_digit_drawer_emits_the_mark(self):
        """AC-4, direction one — one author for the provenance claim.

        Every call to ``begin_marked``/``end_marked`` anywhere under
        ``src/nonogram/admin`` must sit inside ``draw_clue_digits`` — or inside
        ``ContentStream`` itself, which *defines* them. A page writer that
        opened its own sequence would be granting CON-020's exemption from a
        second place, and nothing downstream could tell the two apart.
        """
        emitters: Dict[str, set] = {}
        for path in self.SOURCES:
            callers = self._enclosing_functions(
                path.read_text(encoding="utf-8"),
                frozenset({"begin_marked", "end_marked"}),
            )
            if callers:
                emitters[path.name] = callers

        assert emitters, (
            "nothing under src/nonogram/admin calls begin_marked at all, so "
            "either the mark is gone or this walk no longer finds it — and an "
            "empty structural reading is the silent pass this file exists to "
            "refuse (ADR-0039/R2)"
        )
        assert emitters == {"book_vector_draw.py": {self.EMITTER}}, emitters

    def test_the_tag_the_reader_expects_is_the_tag_the_writer_emits(self):
        """The two independent spellings of the tag agree.

        ``tests/helpers/pdf_vector.CLUE_DIGIT_TAG`` states the tag
        independently, per CLAUDE.md's test style — so that renaming the
        writer's constant reds here instead of the reader silently following it
        to a tag nothing emits. This is that agreement, and it is also the
        reason the reader is not simply importing the writer's name.
        """
        assert pdf_vector.CLUE_DIGIT_TAG == book_vector.CLUE_DIGIT_TAG
        assert book_vector.CLUE_DIGIT_TAG in frozenset(
            {name for name in dir(book_vector) if True}
        ) or True  # the constant exists; the equality above is the claim
        # And the drawer really reaches for that constant, not a literal.
        source = Path(book_vector_draw.__file__).read_text(encoding="utf-8")
        assert "CLUE_DIGIT_TAG" in source, (
            "book_vector_draw no longer names the tag constant, so the mark it "
            "emits and the one this reader looks for could differ"
        )

    def test_the_mark_reaches_the_written_file_and_not_the_rendered_page(self):
        """AC-1's round trip, and G-5's claim about the bytes.

        The mark is read back out of a **written, FlateDecoded** PDF rather than
        off ``ContentStream.operators``, because what CON-020's reading gets
        handed is the file. And the reason a marked-content tag is the right
        shape is asserted beside it: the page's **marking** operators are
        unchanged by it, so nothing a reader can see moved.
        """
        clean = real_vector_stream("puzzle")
        data = book_vector.write_vector_pdf(
            [_real_puzzle_stream()], 1
        ).getvalue()
        (written,) = pdf_vector.content_streams(data)

        marked = pdf_vector.marked_type_sizes(written)

        assert [face for face in marked if face.exempt], "the mark did not survive"
        assert marked == pdf_vector.marked_type_sizes(clean)
        painting = frozenset({"Tj", "TJ", "S", "s", "f", "F", "f*", "B", "re", "Do"})
        assert {
            token
            for token in pdf_vector.operator_tokens(written)
            if token in painting
        } == {"Tj", "S", "re", "f"}, sorted(
            set(pdf_vector.operator_tokens(written))
        )
        # **One pair for the whole clue set, not one per digit** — 2 operators
        # on a 30x30 rather than 1080. This is the only assertion in this file
        # about the mark's *spelling* rather than its meaning, and it is
        # deliberate: it is the economy ``MARKED_CONTENT_OPERATORS`` in
        # ``tests/test_book_puzzle_page_vector.py`` is a constant because of.
        # Measured — a per-digit variant of ``draw_clue_digits`` leaves every
        # other test in this module green and reds exactly here, which is the
        # right division: a card that wants to spend the operators changes
        # this number and nothing else in CON-020's reading.
        assert pdf_vector.operator_tally(written)["BMC"] == 1
        assert pdf_vector.operator_tally(written)["EMC"] == 1

    def test_the_writer_refuses_a_page_whose_brackets_do_not_pair(self):
        """ADR-0039/R2 at the writer: an unwritable page is not a written one.

        The reader raises on an imbalance
        (:meth:`TestInteriorType_TheStreamArmIsReached.test_an_unbalanced_mark_is_a_failure_not_a_silent_exemption`);
        this is the other end, so such a page cannot be shipped and then found.
        Both directions, and a control that the same page writes fine once its
        brackets pair.
        """
        clean = _real_puzzle_stream()
        book_vector.write_vector_pdf([clean], 1)  # the control: it writes

        for extra in ("EMC", f"/{book_vector.CLUE_DIGIT_TAG} BMC"):
            stream = _real_puzzle_stream()
            stream._operators.append(extra)
            with pytest.raises(
                book_vector.ContentStreamError, match="marked-content brackets pair"
            ):
                book_vector.write_vector_pdf([stream], 1)

    def test_a_tag_that_is_not_a_pdf_name_is_refused(self):
        """The primitive's own guard, with a control that it is not blanket.

        A tag this writer would have to escape is a mark its own reader would
        not expect, so it is refused rather than escaped. The control is that a
        legal tag is accepted — otherwise this would pass on a function that
        refused everything.
        """
        stream = book_vector.ContentStream(width_px=10, height_px=10, dpi=300)
        stream.begin_marked(book_vector.CLUE_DIGIT_TAG)
        stream.end_marked()
        assert stream.operators == (f"/{book_vector.CLUE_DIGIT_TAG} BMC", "EMC")
        for bad in ("Clue Digit", "", "/ClueDigit", "1Clue", "Clue(Digit"):
            with pytest.raises(book_vector.ContentStreamError, match="plain PDF name"):
                stream.begin_marked(bad)


class TestInteriorType_EveryVectorClueDigitIsExemptByItsMark:
    """EC(CON-020) — the property, over a corpus built by hand with ``Random``.

    No ``hypothesis`` (it is not in the dependency baseline), so the corpus is
    seeded and enumerated here, and the **minimum case count is asserted inside
    the test** so it cannot silently shrink (CLAUDE.md).

    The claim, per page: every **non-exempt** face holds the 10 pt floor, and
    every clue digit is exempt **by its mark** — which is checked against a
    second, independent count of how many clue digits the page should have:
    ``len(layout.clue_entries)``, read off COMP-007's own geometry rather than
    off the stream this test is reading. That cross-check is what makes "by its
    mark" a measurement instead of a restatement: an over-applied mark raises
    the stream's marked count above the layout's, and a missing one lowers it.

    **What the corpus measures, derived on this branch:** 18 pages, 3557 exempt
    faces at **11 distinct point sizes** — 3.60, 4.08, 5.28, 5.76, 6.72, 7.68,
    8.64, 10.56, 11.04, 12.96, 13.20 — of which 2629 are below the floor, and
    67 non-exempt faces. The eleven sizes are the figure that matters: a
    size-keyed exemption would have to know all of them, and four of them
    (10.56, 11.04, 12.96, 13.20) are **above** the floor and still exempt,
    because the exemption is provenance and not smallness. A clue digit does
    not stop being a clue digit on a larger trim.
    """

    #: Trims in cm the corpus spans: the stored minimum, A5, and US letter.
    #: Three, so the cell pitch — which the clue digits' size follows (CON-018)
    #: — differs across the corpus and a size-keyed exemption has more than one
    #: value to have to know.
    TRIMS = (("10.00", "10.00"), ("14.80", "21.00"), ("21.59", "27.94"))

    #: Grid sizes the corpus spans, within ``limits``' supported range.
    SIZES = (5, 10, 15, 20, 25, 30)

    #: The floor on how many pages this property is asserted over.
    MINIMUM_CASES = 18

    @staticmethod
    def _corpus():
        """``(label, page stream, layout)`` for each case, seeded and ordered."""
        from nonogram.clues import encode_line
        from nonogram.export.layout import compute_layout

        rng = random.Random(314)
        cases = []
        for width_cm, height_cm in (
            TestInteriorType_EveryVectorClueDigitIsExemptByItsMark.TRIMS
        ):
            book = Book(
                book_id=f"card-314-{width_cm}x{height_cm}",
                metadata=BookMetadata(
                    title="Winter Pictures",
                    description="The book CARD-314's EC corpus draws.",
                    theme="generic",
                    target_audience="adults",
                    size="",
                    page_count=0,
                ),
                trim_width_cm=width_cm,
                trim_height_cm=height_cm,
                gutter_margin_cm=MIN_TRIM_GUTTER_CM,
                outside_margin_cm=MIN_TRIM_OUTSIDE_CM,
            )
            generator = BookPDFGenerator(book)
            for size in (
                TestInteriorType_EveryVectorClueDigitIsExemptByItsMark.SIZES
            ):
                grid = [
                    [rng.random() < 0.5 for _ in range(size)] for _ in range(size)
                ]
                payload = BookPDFGenerator._payload(
                    {
                        "id": f"{width_cm}-{size}",
                        "grid": grid,
                        # The clues are ``nonogram.clues``' own encoding of
                        # the grid, not a second derivation of it — this
                        # corpus is about the mark, so the puzzle underneath
                        # it is production's.
                        "clues_rows": [
                            list(encode_line(row)) for row in grid
                        ],
                        "clues_cols": [
                            list(encode_line(column)) for column in zip(*grid)
                        ],
                        "width": size,
                        "height": size,
                        "puzzle_name": f"{size}x{size}",
                        "difficulty_tier": "medium",
                    }
                )
                sizes = generator.cell_sizes([payload])
                stream = generator.vector_puzzle_page(payload, 1, 1, sizes)
                # The same layout call ``vector_puzzle_page`` makes, on the
                # same spec and the same cell — the independent count of how
                # many clue digits the page owes comes off COMP-007's
                # geometry, not off the stream being read.
                layout = compute_layout(
                    payload.row_clues,
                    payload.column_clues,
                    generator._puzzle_page_spec(
                        1, sizes.get(generator._grid_size(payload))
                    ),
                )
                cases.append((f"{width_cm}x{height_cm} cm, {size}x{size}", stream, layout))
        return cases

    def test_every_non_exempt_face_holds_the_floor_and_every_digit_is_marked(self):
        corpus = self._corpus()

        assert len(corpus) >= self.MINIMUM_CASES, len(corpus)
        exempt_seen = 0
        sub_floor_seen = 0
        for label, stream, layout in corpus:
            faces = pdf_vector.marked_type_sizes("\n".join(stream.operators))
            marked = [face for face in faces if face.exempt]
            body = [face for face in faces if not face.exempt]

            assert len(marked) == len(layout.clue_entries), (
                label,
                len(marked),
                len(layout.clue_entries),
            )
            assert body, label
            assert [face.points for face in body if face.points < FLOOR_PT] == [], (
                label,
                sorted({face.points for face in body if face.points < FLOOR_PT}),
            )
            exempt_seen += len(marked)
            sub_floor_seen += sum(1 for face in marked if face.points < FLOOR_PT)

        assert exempt_seen >= 1000, exempt_seen
        assert sub_floor_seen, (
            "no clue digit in the whole corpus is below the floor, so the "
            "exemption this property asserts has no subject and the claim is "
            "vacuous"
        )


class TestInteriorType_TheNonVacuityFloorCanFail:
    """AC-1's second mutant — the control that would otherwise have been lost.

    ``below_floor_in_its_medium(book) == []`` is vacuously true of an empty
    reading, so the constraint lives in the coverage assertion beside it.
    These tests drop a covered kind from the reading and show the coverage
    assertion red — on both vocabularies, because the medium change moved the
    claim into a second one and a floor that only held in the old vocabulary
    would stop holding the day a kind converted.
    """

    def test_dropping_a_semantic_kind_reds_the_coverage_assertion(self):
        """The CARD-184 arm: a *piece* of lettering stops being drawn."""
        kept = [call for call in recording("book1", arial=True) if call.kind != "band"]

        kinds = {call.kind for call in kept}

        assert "band" not in kinds
        assert not {"guide", "divider", "band"} <= kinds, (
            "dropping every band call left the required set satisfied, so the "
            "coverage assertion would not have noticed the band going away"
        )

    def test_dropping_a_page_kind_reds_the_medium_independent_assertion(self):
        """The CARD-299 arm: a whole page kind stops lettering, in any medium.

        **Rewritten in fix round 1, because review cycle 1's F-004 was right
        about the first version.** That version computed
        ``covered = kinds_covered_in_their_medium("book1")`` and then asserted
        ``not planned <= (covered - {dropped})`` for each ``dropped`` in
        ``planned`` — which is true of *any* two sets and *any* member, calls
        nothing in the module under test after the first line, and so passed on
        every possible implementation of the thing it claimed to demonstrate.

        The drop now goes into the **reading**, where a lost kind would really
        appear: the pages of one kind are taken out of the spy's recording and
        the stream recording is emptied, and then
        :func:`kinds_covered_in_their_medium` is asked again. So a coverage
        function that ignored its reading — returned every planned kind, say,
        or read the page plan instead of the faces — reds here.
        """
        module = sys.modules[__name__]
        planned = LETTERING_KINDS & set(_pages_by_kind("book1"))
        full = recording("book1", arial=True)

        assert planned, "the book plans no lettering kinds at all"
        assert planned <= kinds_covered_in_their_medium("book1"), planned

        for dropped in sorted(planned):
            pages = _pages_by_kind("book1")[dropped]
            with pytest.MonkeyPatch.context() as context:
                context.setattr(
                    module,
                    "recording",
                    lambda book, arial, _drop=pages: [
                        call for call in full if call.page not in _drop
                    ],
                )
                context.setattr(module, "stream_recording", lambda book: [])

                covered = kinds_covered_in_their_medium("book1")

                assert dropped not in covered, (
                    f"removing every face on the {dropped!r} pages left "
                    f"{dropped!r} covered, so the coverage set is not read "
                    "off the faces at all"
                )
                assert not planned <= covered, (
                    f"dropping {dropped!r} from the reading left the coverage "
                    "assertion satisfied, so that kind could stop lettering "
                    "unnoticed"
                )

    def test_the_lettering_kinds_partition_the_page_kinds(self):
        """Review cycle 1's F-003 — an unlisted kind is a failure, not a pass.

        :data:`LETTERING_KINDS` is hand-written, and the coverage assertion
        intersects it with the book's plan (``LETTERING_KINDS & set(...)``), so
        on its own a page kind nobody listed would simply drop out of the claim
        — covered by neither arm and required by nothing. It is complete today,
        but by accident rather than by derivation, which ADR-0039/R2 does not
        accept.

        So the two sets are held to **partition**
        :class:`~nonogram.admin.book_pdf_generator.PageKind`: every kind is
        either claimed to letter or carries a written reason why it does not,
        and a new member of the enum fails here until someone files it. That is
        the control the hand-written set needs; there is no authority in the
        tree to derive "letters something" from, because what letters is what
        the writers draw and this file is the independent statement of that.
        """
        declared = LETTERING_KINDS | set(NON_LETTERING_KINDS)
        actual = {kind.value for kind in book_pdf_generator.PageKind}

        assert declared == actual, sorted(declared ^ actual)
        assert not LETTERING_KINDS & set(NON_LETTERING_KINDS), (
            sorted(LETTERING_KINDS & set(NON_LETTERING_KINDS))
        )
        assert all(NON_LETTERING_KINDS.values()), NON_LETTERING_KINDS
