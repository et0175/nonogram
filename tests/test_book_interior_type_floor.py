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

import sys
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

import pytest
from PIL import Image, ImageDraw, ImageFont

from nonogram.admin import book_pdf_generator
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
LETTERING_KINDS = frozenset({"guide", "toc", "divider", "puzzle", "answer"})


@dataclass(frozen=True)
class StreamFace:
    """One ``Tf`` size a written interior page set, read off the shipped file.

    The sibling of :class:`TextCall` for a page of operators, and
    deliberately **poorer**: a content stream records no call chain, so
    ``kind`` here is the page's own :class:`PageKind` value and not one of the
    spy's five semantic kinds, and :attr:`exempt` has no provenance to key on.
    Both losses are stated rather than papered over — see
    :meth:`exempt` and this file's raised finding on CON-020's clue digits.
    """

    page: int
    kind: str
    points: float

    def describe(self) -> str:
        return f"page {self.page} {self.kind} (stream): {self.points:.2f} pt"


def stream_faces(generator: BookPDFGenerator, puzzles) -> List[StreamFace]:
    """Every ``Tf`` size the written interior sets, on its operator pages only.

    The page kinds come from the generator's own **page plan** and the sizes
    from the **file**, zipped ``strict=True``, so a plan that does not describe
    the file it wrote is a failure rather than a short walk — the same pairing
    ``tests/test_book_pdf.py::_media_by_kind`` uses, and for the same reason.
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
        assert kind.value != "puzzle", (
            f"interior page {number} is a VECTOR puzzle page, and CON-020's "
            "clue-digit exemption has no counterpart in a content stream: the "
            "exemption is keyed on the function that draws (png._draw_clues / "
            "_write_clues) and a stream records no provenance. Measured on "
            "this branch, a real vector puzzle page sets 205 Tf operands at "
            "8.64 pt and 14.16 pt, and the 8.64 pt digits are exactly the "
            "exempt ones — so a stream-read floor cannot tell them from body "
            "type. The card that converts the puzzle page owes the stream a "
            "way to mark its clue digits; see CARD-299's raised finding."
        )
        faces.extend(
            StreamFace(number, kind.value, size)
            for size in pdf_vector.type_sizes(stream)
        )
    return faces


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
    """
    return below_floor(recording(book, arial=True)) + [
        face.describe()
        for face in stream_recording(book)
        if face.points < FLOOR_PT
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
        book will hold. ``type_sizes`` is wrapped rather than asserted *about*,
        because the question is whether the arm **called** it: a reader that
        fell through to the spy would leave the wrapper untouched and the
        recorded page list empty.
        """
        monkeypatch.delitem(
            book_pdf_generator._RASTER_DECLARATIONS,
            book_pdf_generator.PageKind.TITLE,
        )
        asked: List[str] = []
        original = pdf_vector.type_sizes
        monkeypatch.setattr(
            pdf_vector,
            "type_sizes",
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

        It is also the whole of the finding: those 8.64 pt digits are exactly
        the ones CON-020 **exempts**, and nothing in the stream says so. The
        exemption is keyed on the drawing function (``png._draw_clues`` /
        ``_write_clues``) and a content stream records no provenance, so this
        floor cannot honour the exemption it must honour. That is why
        :func:`stream_faces` refuses a vector puzzle page by name instead of
        reporting 205 false violations or exempting 8.64 pt by its value.
        """
        generator = BookPDFGenerator(corpus_book())
        payload = BookPDFGenerator._payload(baseline_puzzles()[0])
        sizes = generator.cell_sizes([payload])
        stream = "\n".join(
            generator.vector_puzzle_page(payload, 1, 1, sizes).operators
        )

        found = pdf_vector.type_sizes(stream)

        assert sorted(set(found)) == [8.64, 14.16], sorted(set(found))
        assert [size for size in found if size < FLOOR_PT], (
            "a vector puzzle page sets nothing below the floor, so this "
            "card's finding about the clue-digit exemption has no subject"
        )

    def test_a_vector_puzzle_page_refuses_rather_than_reading_its_clue_digits(
        self, monkeypatch
    ):
        """The default-DENY arm: an unreadable shape FAILS (ADR-0039/R2).

        The one page kind whose exemption the stream cannot express is refused
        by name, naming what it would take to read it. A reading that instead
        skipped the page, or exempted 8.64 pt because that is what clue digits
        happen to measure, would be the silent pass the rule forbids — the
        second would exempt a *body* face that happened to be 8.64 pt.
        """
        monkeypatch.setattr(
            pdf_vector,
            "page_media",
            lambda _data: [pdf_vector.VECTOR] * 14,
        )
        with pytest.raises(AssertionError, match="VECTOR puzzle page"):
            stream_faces(BookPDFGenerator(corpus_book()), baseline_puzzles())


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

        This is the arm that keeps CON-020 real after a kind converts. The
        drop is applied to the covered set rather than to the generator,
        because what is being tested is the **assertion**, not the writer: the
        question is whether `planned <= covered` can fail, and it can.
        """
        planned = LETTERING_KINDS & set(_pages_by_kind("book1"))
        covered = kinds_covered_in_their_medium("book1")

        assert planned, "the book plans no lettering kinds at all"
        assert planned <= covered, (planned, covered)

        for dropped in sorted(planned):
            assert not planned <= (covered - {dropped}), (
                f"dropping {dropped!r} from the covered set left the coverage "
                "assertion satisfied, so that kind could stop lettering "
                "unnoticed"
            )
